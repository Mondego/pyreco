__FILENAME__ = feeds
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.utils.feedgenerator import rfc3339_date

from django_push.publisher.feeds import Feed, HubAtom1Feed
from activity.models import Activity
from projects.models import Project
from users.models import UserProfile


class ActivityStreamAtomFeed(HubAtom1Feed):

    def root_attributes(self):
        attrs = super(ActivityStreamAtomFeed, self).root_attributes()
        attrs['xmlns:activity'] = 'http://activitystrea.ms/spec/1.0/'
        return attrs

    def _add_author_info(self, handler, author_name, author_link):
        handler.startElement(u'author', {})
        handler.addQuickElement(u'activity:object-type',
                                'http://activitystrea.ms/schema/1.0/person')
        handler.addQuickElement(u'name', author_name)
        handler.addQuickElement(u'uri', author_link)
        handler.endElement(u'author')

    def add_root_elements(self, handler):
        if self.feed['author_name'] is not None:
            self._add_author_info(
                handler, self.feed['author_name'], self.feed['author_link'])
        super(ActivityStreamAtomFeed, self).add_root_elements(handler)

    def add_item_elements(self, handler, item):
        handler.addQuickElement(u'updated', rfc3339_date(item['updated']))
        if item['author_name'] is not None:
            self._add_author_info(
                handler, item['author_name'], item['author_link'])
        item['author_name'] = None
        handler.addQuickElement(u'activity:verb', item['activity']['verb'])
        obj = item['activity']['object']
        handler.startElement(u'activity:object', {})
        handler.addQuickElement(u'activity:object-type', obj['object-type'])
        handler.addQuickElement(u'link', u'', {
            'href': obj['link'],
            'rel': 'alternate',
            'type': 'text/html',
        })
        handler.addQuickElement(
            u'content', obj['content'], {'type': 'text/html'})
        handler.endElement(u'activity:object')
        super(ActivityStreamAtomFeed, self).add_item_elements(handler, item)


class UserActivityFeed(Feed):
    """Atom feed of user activities."""

    feed_type = ActivityStreamAtomFeed

    def item_author_name(self, item):
        return item.actor.name

    def item_author_link(self, item):
        return self._request.build_absolute_uri(item.actor.get_absolute_url())

    def title(self, user):
        return user and user.name or _('Public Activity')

    def subtitle(self, user):
        if user:
            return _('Activity feed for %s' % (user.name,))
        else:
            return _('Public Activity')

    def link(self, user):
        return reverse('users_profile_view',
                       kwargs={'username': user.username})

    def get_object(self, request, username):
        self._request = request
        return get_object_or_404(UserProfile, username=username)

    def items(self, user):
        return Activity.objects.filter(actor=user).order_by('-created_on')[:25]

    def item_title(self, item):
        return item.textual_representation()

    def item_description(self, item):
        return item.html_representation()

    def item_link(self, item):
        return self._request.build_absolute_uri(item.get_absolute_url())

    def item_extra_kwargs(self, item):
        return {
            'updated': item.created_on,
            'activity': {
                'verb': item.verb,
                'object': {
                    'object-type': item.object_type,
                    'link': self._request.build_absolute_uri(item.object_url),
                    'content': item.html_representation(),
                },
            },
        }


class ProjectActivityFeed(UserActivityFeed):
    """Atom feed of project activities."""

    def title(self, project):
        return project.name

    def get_object(self, request, project):
        self._request = request
        return get_object_or_404(Project, slug=project)

    def items(self, project):
        return Activity.objects.filter(
            Q(target_project=project) | Q(project=project),
        ).order_by('-created_on')[:25]

    def link(self, project):
        return reverse('projects_show', kwargs={'slug': project.slug})


class DashboardFeed(UserActivityFeed):
    """Atom feed of activities from a users dashboard."""

    def get_object(self, request):
        self._request = request
        if request.user.is_authenticated():
            return request.user.get_profile()
        else:
            return None

    def items(self, user):
        if user is None:
            return Activity.objects.public()
        user_ids = [u.pk for u in user.following()]
        project_ids = [p.pk for p in user.following(model=Project)]
        return Activity.objects.select_related(
            'actor', 'status', 'project', 'remote_object',
            'remote_object_link', 'target_project').filter(
            Q(actor__exact=user) | Q(actor__in=user_ids) |
            Q(project__in=project_ids),
       ).order_by('-created_on')[0:25]

    def link(self, user):
        return reverse('dashboard_index')

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'RemoteObject'
        db.create_table('activity_remoteobject', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_type', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('link', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['links.Link'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('uri', self.gf('django.db.models.fields.URLField')(max_length=200, null=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('activity', ['RemoteObject'])

        # Adding model 'Activity'
        db.create_table('activity_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('actor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.UserProfile'])),
            ('verb', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['statuses.Status'], null=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'], null=True)),
            ('target_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='target_user', null=True, to=orm['users.UserProfile'])),
            ('remote_object', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activity.RemoteObject'], null=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activity.Activity'], null=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('activity', ['Activity'])


    def backwards(self, orm):

        # Deleting model 'RemoteObject'
        db.delete_table('activity_remoteobject')

        # Deleting model 'Activity'
        db.delete_table('activity_activity')


    models = {
        'activity.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.Activity']", 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'remote_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.RemoteObject']", 'null': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['statuses.Status']", 'null': 'True'}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_user'", 'null': 'True', 'to': "orm['users.UserProfile']"}),
            'verb': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'activity.remoteobject': {
            'Meta': {'object_name': 'RemoteObject'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['links.Link']"}),
            'object_type': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
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
        },
        'links.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriber.Subscription']", 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        },
        'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['activity']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_activity_target_project
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Activity.target_project'
        db.add_column('activity_activity', 'target_project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='target_project', null=True, to=orm['projects.Project']), keep_default=True)


    def backwards(self, orm):
        
        # Deleting field 'Activity.target_project'
        db.delete_column('activity_activity', 'target_project_id')


    models = {
        'activity.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.Activity']", 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'remote_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.RemoteObject']", 'null': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['statuses.Status']", 'null': 'True'}),
            'target_project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_project'", 'null': 'True', 'to': "orm['projects.Project']"}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_user'", 'null': 'True', 'to': "orm['users.UserProfile']"}),
            'verb': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'activity.remoteobject': {
            'Meta': {'object_name': 'RemoteObject'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['links.Link']"}),
            'object_type': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
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
        },
        'links.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriber.Subscription']", 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 31)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 31)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        },
        'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 31)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['activity']

########NEW FILE########
__FILENAME__ = models
from django.db import models, connection
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from drumbeat.models import ModelBase, ManagerBase
from activity import schema


class RemoteObject(models.Model):
    """Represents an object originating from another system."""
    object_type = models.URLField(verify_exists=False)
    link = models.ForeignKey('links.Link')
    title = models.CharField(max_length=255)
    uri = models.URLField(null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return self.uri


class ActivityManager(ManagerBase):

    def public(self):
        """Get list of activities to show on splash page."""

        def _query_list(query):
            cursor = connection.cursor()
            cursor.execute(query)
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                yield row[0]

        activity_ids = _query_list("""
            SELECT a.id
            FROM activity_activity a
            INNER JOIN users_userprofile u ON u.id = a.actor_id
            WHERE u.display_name IS NOT NULL
                AND a.parent_id IS NULL
                AND u.image IS NOT NULL
                AND u.image != ''
                AND a.verb != 'http://activitystrea.ms/schema/1.0/follow'
            GROUP BY a.actor_id
            ORDER BY a.created_on DESC LIMIT 10;
        """)
        return Activity.objects.filter(
            id__in=activity_ids).order_by('-created_on')

    def dashboard(self, user):
        """
        Given a user, return a list of activities to show on their dashboard.
        """
        projects_following = user.following(model='Project')
        users_following = user.following()
        project_ids = [p.pk for p in projects_following]
        user_ids = [u.pk for u in users_following]
        return Activity.objects.select_related(
            'actor', 'status', 'project', 'remote_object',
            'remote_object__link', 'target_project').filter(
            models.Q(actor__exact=user) |
            models.Q(actor__in=user_ids) | models.Q(project__in=project_ids),
        ).exclude(
            models.Q(verb='http://activitystrea.ms/schema/1.0/follow'),
            models.Q(target_user__isnull=True),
            models.Q(project__in=project_ids),
        ).exclude(
            models.Q(verb='http://activitystrea.ms/schema/1.0/follow'),
            models.Q(actor=user),
        ).exclude(parent__isnull=False).exclude(
            models.Q(status__in_reply_to__isnull=False),
        ).order_by('-created_on')[0:25]

    def for_user(self, user):
        """Return a list of activities where the actor is user."""
        return Activity.objects.select_related(
            'actor', 'status', 'project').filter(
            actor=user,
        ).exclude(
            models.Q(verb='http://activitystrea.ms/schema/1.0/follow'),
            models.Q(target_user__isnull=False),
        ).exclude(
            models.Q(status__in_reply_to__isnull=False),
        ).order_by('-created_on')[0:25]


class Activity(ModelBase):
    """Represents a single activity entry."""
    actor = models.ForeignKey('users.UserProfile')
    verb = models.URLField(verify_exists=False)
    status = models.ForeignKey('statuses.Status', null=True)
    project = models.ForeignKey('projects.Project', null=True)
    target_user = models.ForeignKey('users.UserProfile', null=True,
                                    related_name='target_user')
    target_project = models.ForeignKey('projects.Project', null=True,
                                       related_name='target_project')
    remote_object = models.ForeignKey(RemoteObject, null=True)
    parent = models.ForeignKey('self', null=True, related_name='comments')
    created_on = models.DateTimeField(auto_now_add=True)

    objects = ActivityManager()

    @models.permalink
    def get_absolute_url(self):
        return ('activity_index', (), {
            'activity_id': self.pk,
        })

    @property
    def object_type(self):
        obj = self.status or self.target_user or self.remote_object or None
        return obj and obj.object_type or None

    @property
    def object_url(self):
        obj = self.status or self.target_user or self.remote_object or None
        return obj and obj.get_absolute_url() or None

    def textual_representation(self):
        target = self.target_user or self.target_project or self.project
        if target and self.verb == schema.verbs['follow']:
            return "%s %s %s" % (
                self.actor.name, schema.past_tense['follow'],
                target.name)
        if self.status:
            return self.status.status
        elif self.remote_object:
            return self.remote_object.title
        friendly_verb = schema.verbs_by_uri[self.verb]
        return _("%s activity performed by %s") % (friendly_verb,
                                                   self.actor.name)

    def html_representation(self):
        return render_to_string('activity/_activity_body.html', {
            'activity': self,
            'show_actor': True,
        })

    def __unicode__(self):
        return _("Activity ID %d. Actor id %d, Verb %s") % (
            self.pk, self.actor.pk, self.verb)

########NEW FILE########
__FILENAME__ = schema
from django.utils.translation import ugettext_lazy as _lazy

# a list of verbs defined in the activity schema
verbs = {
    'favorite': 'http://activitystrea.ms/schema/1.0/favorite',
    'follow': 'http://activitystrea.ms/schema/1.0/follow',
    'like': 'http://activitystrea.ms/schema/1.0/like',
    'make-friend': 'http://activitystrea.ms/schema/1.0/make-friend',
    'join': 'http://activitystrea.ms/schema/1.0/join',
    'play': 'http://activitystrea.ms/schema/1.0/play',
    'post': 'http://activitystrea.ms/schema/1.0/post',
    'save': 'http://activitystrea.ms/schema/1.0/save',
    'share': 'http://activitystrea.ms/schema/1.0/share',
    'tag': 'http://activitystrea.ms/schema/1.0/tag',
    'update': 'http://activitystrea.ms/schema/1.0/update',
    'rsvp-yes': 'http://activitystrea.ms/schema/1.0/rsvp-yes',
    'rsvp-no': 'http://activitystrea.ms/schema/1.0/rsvp-no',
    'rsvp-maybe': 'http://activitystrea.ms/schema/1.0/rsvp-maybe',
}

verbs_by_uri = {}
for key, value in verbs.iteritems():
    verbs_by_uri[value] = key

past_tense = {
    'favorite': _lazy('favorited'),
    'follow': _lazy('started following'),
    'like': _lazy('liked'),
    'make-friend': _lazy('is now friends with'),
    'join': _lazy('joined'),
    'play': _lazy('played'),
    'post': _lazy('posted'),
    'save': _lazy('saved'),
    'share': _lazy('shared'),
    'tag': _lazy('tagged'),
    'update': _lazy('updated'),
    'rsvp-yes': _lazy('is attending'),
    'rsvp-no': _lazy('is not attending'),
    'rsvp-maybe': _lazy('might be attending'),
}

# a list of base object types defined in the activity schema
object_types = {
    'article': 'http://activitystrea.ms/schema/1.0/article',
    'audio': 'http://activitystrea.ms/schema/1.0/audio',
    'bookmark': 'http://activitystrea.ms/schema/1.0/bookmark',
    'comment': 'http://activitystrea.ms/schema/1.0/comment',
    'file': 'http://activitystrea.ms/schema/1.0/file',
    'folder': 'http://activitystrea.ms/schema/1.0/folder',
    'group': 'http://activitystrea.ms/schema/1.0/group',
    'note': 'http://activitystrea.ms/schema/1.0/note',
    'person': 'http://activitystrea.ms/schema/1.0/person',
    'photo': 'http://activitystrea.ms/schema/1.0/photo',
    'photo-album': 'http://activitystrea.ms/schema/1.0/photo-album',
    'place': 'http://activitystrea.ms/schema/1.0/place',
    'playlist': 'http://activitystrea.ms/schema/1.0/playlist',
    'product': 'http://activitystrea.ms/schema/1.0/product',
    'review': 'http://activitystrea.ms/schema/1.0/review',
    'service': 'http://activitystrea.ms/schema/1.0/service',
    'status': 'http://activitystrea.ms/schema/1.0/status',
    'video': 'http://activitystrea.ms/schema/1.0/video',
    'event': 'http://activitystrea.ms/schema/1.0/event',
}

########NEW FILE########
__FILENAME__ = activity_tags
import datetime

from django import template
from django.template.defaultfilters import timesince
from django.utils.translation import ugettext as _

from activity import schema

register = template.Library()


@register.filter
def truncate(value, arg):
    """
    Truncates a string after a given number of chars
    Argument: Number of chars to truncate after
    """
    try:
        length = int(arg)
    except ValueError:  # invalid literal for int()
        return value  # Fail silently.
    if not isinstance(value, basestring):
        value = str(value)
    if (len(value) > length):
        return value[:length] + "..."
    else:
        return value


@register.filter
def should_hyperlink(activity):
    if activity.verb == schema.verbs['follow']:
        return True
    if activity.project:
        return True
    if not activity.remote_object:
        return False
    if not activity.remote_object.uri:
        return False
    if activity.remote_object.object_type != schema.object_types['article']:
        return False
    return True


@register.filter
def get_link(activity):
    if activity.remote_object and activity.remote_object.uri:
        return activity.remote_object.uri
    if activity.target_user:
        return activity.target_user.get_absolute_url()


@register.filter
def get_link_name(activity):
    if activity.remote_object:
        return activity.remote_object.title
    if activity.target_user:
        return activity.target_user.name


@register.filter
def activity_representation(activity):
    if activity.status:
        return activity.status
    if activity.remote_object:
        if activity.remote_object.title:
            return activity.remote_object.title
    if activity.project:
        return activity.project
    return None


@register.filter
def should_show_verb(activity):
    if activity.status:
        return False
    if activity.remote_object:
        return False
    return True


@register.filter
def friendly_verb(activity):
    try:
        verb = schema.verbs_by_uri[activity.verb]
        return schema.past_tense[verb].capitalize()
    except KeyError:
        return activity.verb


@register.filter
def created_on(activity):
    now = datetime.datetime.now()
    delta = now - activity.created_on
    if delta > datetime.timedelta(days=2):
        return activity.created_on.strftime("%d %b %Y")
    return timesince(activity.created_on) + _(" ago")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from activity import feeds


urlpatterns = patterns('',
    url(r'^activity/(?P<activity_id>[\d]+)/$', 'activity.views.index',
        name='activity_index'),
    url(r'^(?P<username>[\w\-\. ]+)/feed$', feeds.UserActivityFeed(),
        name='activity_user_feed'),
    url(r'^projects/(?P<project>[\w\- ]+)/feed$', feeds.ProjectActivityFeed(),
        name='activity_project_feed'),
    url(r'^feed$', feeds.DashboardFeed(),
        name='activity_dashboard_feed'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext

from activity.models import Activity


def index(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)
    return render_to_response('activity/index.html', {
        'activity': activity,
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = build_files
# Build file based largely around that used in playdoh:
# https://github.com/jsocol/jingo-minify/blob/master/jingo_minify/management/commands/compress_assets.py

import os
from subprocess import call, PIPE

from django.conf import settings
from django.core.management.base import BaseCommand

import git

path = lambda *a: os.path.join(settings.MEDIA_ROOT, *a)

class Command(BaseCommand):
    help = ("Compress and concatinate css and js assets held in settings.ASSETS to live file names held in each settings.ASSETS dictionary")

    def update_hashes(self):
        def gitid(path):
            id = (git.repo.Repo(os.path.join(settings.ROOT, path)).log('-1')[0].id_abbrev)
            return id

        build_id_file = os.path.realpath(os.path.join(settings.ROOT, 'build.py'))

        with open(build_id_file, 'w') as f:
            f.write('BUILD_ID_CSS = "%s"' % gitid('media/css'))
            f.write("\n")
            f.write('BUILD_ID_JS = "%s"' % gitid('media/js'))
            f.write("\n"),
            f.write('BUILD_ID_JS_INCLUDES = "%s"' % gitid('media/js/include'))

    def handle(self, **options):
        # point to yui compressor
        jar_path = (os.path.dirname(__file__), '..', '..', 'bin', 'yuicompressor-2.4.6.jar')
        path_to_jar = os.path.realpath(os.path.join(*jar_path))
        
        for ftype, bundle in settings.ASSETS.iteritems():
            for name, files in bundle.iteritems():
                files_all = []
                for fn in files['dev']:
                    if fn.endswith('.min.%s' % ftype):
                        files_all.append(fn)
                    else:
                        tmp_location = '%s/tmp' % ftype
                        if not os.path.exists(path(tmp_location)):
                            os.makedirs(path(tmp_location))
                            print 'Creating %s to store compressed files' % path(tmp_location)
                        comp_fn = '%s/%s' % (tmp_location, '%s.min' % fn.split('/')[-1])
                        call('java -jar %s %s -o %s' % (path_to_jar, path(fn), path(comp_fn)), shell=True, stdout=PIPE)
                        files_all.append(comp_fn)
                
                end_file = path(bundle[name]['live'][0].lstrip('/'))
                real_files = [path(f.lstrip('/')) for f in files_all]

                if os.path.exists(end_file):
                    call('cat %s > %s' % (' '.join(real_files), end_file), shell=True)
                else:
                    print '### creating %s ###' % end_file
                    open(end_file, 'w+')
                    call('cat %s > %s' % (' '.join(real_files), end_file), shell=True)

                print '### build_file for %s/%s ###' % (ftype, name)
                print real_files
                print 'merged down into %s' % end_file

        self.update_hashes()

########NEW FILE########
__FILENAME__ = build_id
from django import template
from build import BUILD_ID_JS_INCLUDES

register = template.Library()

@register.simple_tag
def build_id():
   return BUILD_ID_JS_INCLUDES

########NEW FILE########
__FILENAME__ = serve
from django import template
from django.conf import settings

from build import BUILD_ID_CSS, BUILD_ID_JS

register = template.Library()

@register.inclusion_tag('assetmanager/files.html', takes_context=True)
def serve(context, type, area):
    try:
        request = context['request'].GET.get('files')
    except KeyError:
        is_dev = settings.DEBUG
    else:
        if request == "original":
            is_dev = True
        else:
            is_dev = settings.DEBUG

    if is_dev:
        files = settings.ASSETS[type][area]['dev']
    else:
        files = settings.ASSETS[type][area]['live']

    return {
        'files':files, 
        'type':type,
        'root':settings.MEDIA_URL,
        'build':{
             'JS':BUILD_ID_JS,
             'CSS':BUILD_ID_CSS
        }
    }

########NEW FILE########
__FILENAME__ = decorators
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from challenges.models import Challenge, Submission


def challenge_owner_required(func):
    """ check that the current user is the challenge owner """

    def decorator(*args, **kwargs):
        request = args[0]
        challenge = get_object_or_404(Challenge, slug=kwargs['slug'])
        user = request.user.get_profile()

        if user != challenge.created_by:
            return HttpResponseForbidden()
        return func(*args, **kwargs)
    return decorator


def submission_owner_required(func):
    """ check that the current user is the challenge response owner """

    def decorator(*args, **kwargs):
        request = args[0]
        submission = get_object_or_404(Submission,
                                       pk=kwargs['submission_id'])
        user = request.user.get_profile()

        if user != submission.created_by:
            return HttpResponseForbidden()
        return func(*args, **kwargs)
    return decorator

########NEW FILE########
__FILENAME__ = feeds
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django_push.publisher.feeds import Feed, HubAtom1Feed

from projects.models import Project
from challenges.models import Challenge, Submission


class ChallengesFeed(Feed):
    feed_type = HubAtom1Feed

    def items(self):
        return Challenge.objects.active().order_by('-created_on')

    def link(self):
        return reverse('challenges_feed')

    def item_description(self, item):
        return item.brief


class SubmissionsFeed(Feed):
    feed_type = HubAtom1Feed

    def get_object(self, request, challenge):
        return get_object_or_404(Challenge, slug=challenge)

    def items(self, challenge):
        return Submission.objects.filter(challenge=challenge).filter(
            is_published=True).order_by('-created_on')

    def link(self, challenge):
        return reverse('challenges_submissions_feed',
                       kwargs=dict(challenge=challenge.slug))


class ProjectChallengesFeed(ChallengesFeed):

    def get_object(self, request, project):
        return get_object_or_404(Project, slug=project)

    def items(self, project):
        return Challenge.objects.active().filter(project=project).order_by(
            '-created_on')

########NEW FILE########
__FILENAME__ = forms
import logging

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from challenges.models import (Challenge, Submission, Judge,
                               VoterTaxonomy, VoterDetails)
from messages.models import Message
from users.models import UserProfile

log = logging.getLogger(__name__)


class ChallengeForm(forms.ModelForm):
    class Meta:
        model = Challenge
        exclude = ('slug', 'project', 'created_by', 'created_on', 'is_open')


class ChallengeImageForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = ('image',)

    def clean_image(self):
        if self.cleaned_data['image'].size > settings.MAX_IMAGE_SIZE:
            max_size = settings.MAX_IMAGE_SIZE / 1024
            raise forms.ValidationError(
                _("Image exceeds max image size: %(max)dk",
                  dict(max=max_size)))
        return self.cleaned_data['image']


class ChallengeContactForm(forms.Form):
    challenge = forms.IntegerField(required=True, widget=forms.HiddenInput())
    subject = forms.CharField(label=_(u'Subject'))
    body = forms.CharField(
        label=_(u'Body'),
        widget=forms.Textarea(attrs={'rows': '12', 'cols': '55'}),
    )

    def save(self, sender):
        challenge = self.cleaned_data['challenge']
        try:
            challenge = Challenge.objects.get(id=int(challenge))
        except Challenge.DoesNotExist:
            raise forms.ValidationError(_(u'Not a valid challenge'))
        recipients = UserProfile.objects.filter(submissions__challenge=challenge).distinct()
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        message_list = []
        for r in recipients:
            msg = Message(
                sender=sender,
                recipient=r.user,
                subject=subject,
                body=body,
            )
            msg.save()
            message_list.append(msg)
        return message_list


class SubmissionSummaryForm(forms.ModelForm):

    class Meta:
        model = Submission
        fields = ('summary', )


class SubmissionForm(forms.ModelForm):

    class Meta:
        model = Submission
        fields = ('title', 'summary', 'keywords', 'bio')


class SubmissionDescriptionForm(forms.ModelForm):

    class Meta:
        model = Submission
        fields = ('description', )
        widgets = {
            'description': forms.Textarea(attrs={'class': 'wmd'}),
        }


class VoterDetailsForm(forms.ModelForm):
    taxonomy = forms.ModelMultipleChoiceField(
        queryset=VoterTaxonomy.objects.all(),
        required=True, widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = VoterDetails
        fields = ('taxonomy', )

    def clean_taxonomy(self):
        if len(self.cleaned_data['taxonomy']) > 3:
            raise forms.ValidationError('Select no more than 3.')
        return self.cleaned_data['taxonomy']


class JudgeForm(forms.ModelForm):
    class Meta:
        model = Judge
        fields = ('user', )

########NEW FILE########
__FILENAME__ = exportsubmissions
import csv
import sys

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from challenges.models import Submission


class Command(BaseCommand):
    help = 'Export Challenge Submissions'

    def build_absolute_url(self, relative):
        site = Site.objects.get(id=settings.SITE_ID)
        return 'http://' + site.domain + relative

    def handle(self, *args, **options):
        writer = csv.writer(sys.stdout, delimiter='|',
                            quoting=csv.QUOTE_MINIMAL)
        submissions = Submission.objects.filter(is_published=True)
        encode = lambda s: s and s.encode('utf-8') or s
        writer.writerow(('Id', 'Title', 'Summary', 'Description', 'Keywords',
                         'Bio', 'Challenge', 'Created on', 'Created by',
                         'Profile Bio', 'Submission URL'))
        for s in submissions:
            writer.writerow((s.id, encode(s.title), encode(s.summary),
                      encode(s.description), encode(s.keywords), encode(s.bio),
                      encode(s.get_challenge().title),
                      encode(s.created_on.isoformat()),
                      encode(s.created_by.username),
                      encode(s.created_by.bio),
                      encode(self.build_absolute_url(s.get_absolute_url()))))

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Challenge'
        db.create_table('challenges_challenge', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('description_html', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('start_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'])),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='challenges', to=orm['users.UserProfile'])),
            ('is_open', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('challenges', ['Challenge'])

        # Adding model 'Submission'
        db.create_table('challenges_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('description_html', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='submissions', to=orm['users.UserProfile'])),
        ))
        db.send_create_signal('challenges', ['Submission'])

        # Adding M2M table for field challenge on 'Submission'
        db.create_table('challenges_submission_challenge', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('submission', models.ForeignKey(orm['challenges.submission'], null=False)),
            ('challenge', models.ForeignKey(orm['challenges.challenge'], null=False))
        ))
        db.create_unique('challenges_submission_challenge', ['submission_id', 'challenge_id'])


    def backwards(self, orm):
        
        # Deleting model 'Challenge'
        db.delete_table('challenges_challenge')

        # Deleting model 'Submission'
        db.delete_table('challenges_submission')

        # Removing M2M table for field challenge on 'Submission'
        db.delete_table('challenges_submission_challenge')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0002_auto__del_field_submission_slug
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Submission.slug'
        db.delete_column('challenges_submission', 'slug')


    def backwards(self, orm):
        
        # Adding field 'Submission.slug'
        db.add_column('challenges_submission', 'slug', self.gf('django.db.models.fields.SlugField')(default='', max_length=50, unique=True, db_index=True), keep_default=False)


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 2, 4, 11, 0, 10, 786922)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 4)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 4)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0003_auto__add_judge__add_unique_judge_challenge_user
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Judge'
        db.create_table('challenges_judge', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('challenge', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['challenges.Challenge'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='judges', to=orm['users.UserProfile'])),
        ))
        db.send_create_signal('challenges', ['Judge'])

        # Adding unique constraint on 'Judge', fields ['challenge', 'user']
        db.create_unique('challenges_judge', ['challenge_id', 'user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Judge', fields ['challenge', 'user']
        db.delete_unique('challenges_judge', ['challenge_id', 'user_id'])

        # Deleting model 'Judge'
        db.delete_table('challenges_judge')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 2, 23, 10, 28, 27, 574724)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_submission_summary
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Submission.summary'
        db.add_column('challenges_submission', 'summary', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Submission.summary'
        db.delete_column('challenges_submission', 'summary')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 2, 14, 24, 58, 357242)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_submission_created_on__add_field_challenge_created_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Submission.created_on'
        db.add_column('challenges_submission', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2011, 3, 2, 16, 16, 32, 381894), auto_now_add=True, blank=True), keep_default=False)

        # Adding field 'Challenge.created_on'
        db.add_column('challenges_challenge', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2011, 3, 2, 16, 16, 32, 380928), auto_now_add=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Submission.created_on'
        db.delete_column('challenges_submission', 'created_on')

        # Deleting field 'Challenge.created_on'
        db.delete_column('challenges_challenge', 'created_on')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 2, 16, 16, 32, 380928)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 2, 16, 16, 32, 380804)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 2, 16, 16, 32, 381894)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 2)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0006_auto__del_field_challenge_description__del_field_challenge_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Challenge.description'
        db.delete_column('challenges_challenge', 'description')

        # Deleting field 'Challenge.description_html'
        db.delete_column('challenges_challenge', 'description_html')

        # Adding field 'Challenge.title_long'
        db.add_column('challenges_challenge', 'title_long', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)

        # Adding field 'Challenge.brief'
        db.add_column('challenges_challenge', 'brief', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'Challenge.guidelines'
        db.add_column('challenges_challenge', 'guidelines', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'Challenge.important_dates'
        db.add_column('challenges_challenge', 'important_dates', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'Challenge.resources'
        db.add_column('challenges_challenge', 'resources', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'Challenge.rules'
        db.add_column('challenges_challenge', 'rules', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Challenge.description'
        db.add_column('challenges_challenge', 'description', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)

        # Adding field 'Challenge.description_html'
        db.add_column('challenges_challenge', 'description_html', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Deleting field 'Challenge.title_long'
        db.delete_column('challenges_challenge', 'title_long')

        # Deleting field 'Challenge.brief'
        db.delete_column('challenges_challenge', 'brief')

        # Deleting field 'Challenge.guidelines'
        db.delete_column('challenges_challenge', 'guidelines')

        # Deleting field 'Challenge.important_dates'
        db.delete_column('challenges_challenge', 'important_dates')

        # Deleting field 'Challenge.resources'
        db.delete_column('challenges_challenge', 'resources')

        # Deleting field 'Challenge.rules'
        db.delete_column('challenges_challenge', 'rules')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 16, 10, 52, 41, 898566)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 16, 10, 52, 41, 898385)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 16, 10, 52, 41, 903021)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0007_auto__add_votertaxonomy__add_voterdetails
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'VoterTaxonomy'
        db.create_table('challenges_votertaxonomy', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('challenges', ['VoterTaxonomy'])

        # Adding model 'VoterDetails'
        db.create_table('challenges_voterdetails', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='voter_data', to=orm['users.UserProfile'])),
        ))
        db.send_create_signal('challenges', ['VoterDetails'])

        # Adding M2M table for field taxonomy on 'VoterDetails'
        db.create_table('challenges_voterdetails_taxonomy', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('voterdetails', models.ForeignKey(orm['challenges.voterdetails'], null=False)),
            ('votertaxonomy', models.ForeignKey(orm['challenges.votertaxonomy'], null=False))
        ))
        db.create_unique('challenges_voterdetails_taxonomy', ['voterdetails_id', 'votertaxonomy_id'])


    def backwards(self, orm):
        
        # Deleting model 'VoterTaxonomy'
        db.delete_table('challenges_votertaxonomy')

        # Deleting model 'VoterDetails'
        db.delete_table('challenges_voterdetails')

        # Removing M2M table for field taxonomy on 'VoterDetails'
        db.delete_table('challenges_voterdetails_taxonomy')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 23, 17, 39, 8, 846424)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 23, 17, 39, 8, 846312)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 3, 23, 17, 39, 8, 856305)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_data'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_challenge_image
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Challenge.image'
        db.add_column('challenges_challenge', 'image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Challenge.image'
        db.delete_column('challenges_challenge', 'image')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 13, 14, 48, 41, 409274)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 13, 14, 48, 41, 409110)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 13, 14, 48, 41, 423863)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 13)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 13)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0009_auto__chg_field_submission_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Submission.description'
        db.alter_column('challenges_submission', 'description', self.gf('django.db.models.fields.TextField')(null=True))


    def backwards(self, orm):
        
        # Changing field 'Submission.description'
        db.alter_column('challenges_submission', 'description', self.gf('django.db.models.fields.TextField')(default=''))


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 13, 39, 31, 860437)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 13, 39, 31, 860280)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 13, 39, 31, 870177)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 20)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 20)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0010_auto__del_unique_submission_title
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass


    def backwards(self, orm):
        
        # Adding unique constraint on 'Submission', fields ['title']
        db.create_unique('challenges_submission', ['title'])


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 14, 3, 19, 152993)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 14, 3, 19, 152837)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 20, 14, 3, 19, 162578)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 20)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 20)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0011_auto__add_field_challenge_allow_voting
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Challenge.allow_voting'
        db.add_column('challenges_challenge', 'allow_voting', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Challenge.allow_voting'
        db.delete_column('challenges_challenge', 'allow_voting')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 22, 13, 35, 53, 712007)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 22, 13, 35, 53, 711851)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 22, 13, 35, 53, 721872)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0012_auto__add_field_submission_keywords__add_field_submission_bio
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Submission.keywords'
        db.add_column('challenges_submission', 'keywords', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True), keep_default=False)

        # Adding field 'Submission.bio'
        db.add_column('challenges_submission', 'bio', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Submission.keywords'
        db.delete_column('challenges_submission', 'keywords')

        # Deleting field 'Submission.bio'
        db.delete_column('challenges_submission', 'bio')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 24, 14, 47, 5, 430764)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 24, 14, 47, 5, 430423)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 4, 24, 14, 47, 5, 444142)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 24)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 4, 24)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0013_auto__add_field_challenge_entrants_can_edit
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Challenge.entrants_can_edit'
        db.add_column('challenges_challenge', 'entrants_can_edit', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Challenge.entrants_can_edit'
        db.delete_column('challenges_challenge', 'entrants_can_edit')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 8, 14, 6, 0, 73768)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'entrants_can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 8, 14, 6, 0, 73612)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 8, 14, 6, 0, 83734)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0014_auto__add_field_challenge_sidebar__add_field_challenge_above_fold
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Challenge.sidebar'
        db.add_column('challenges_challenge', 'sidebar', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

        # Adding field 'Challenge.above_fold'
        db.add_column('challenges_challenge', 'above_fold', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Challenge.sidebar'
        db.delete_column('challenges_challenge', 'sidebar')

        # Deleting field 'Challenge.above_fold'
        db.delete_column('challenges_challenge', 'above_fold')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'above_fold': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 10, 17, 37, 11, 968847)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'entrants_can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'sidebar': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 10, 17, 37, 11, 968659)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 10, 17, 37, 11, 980075)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 10)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 10)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0015_auto__add_field_submission_is_published
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Submission.is_published'
        db.add_column('challenges_submission', 'is_published', self.gf('django.db.models.fields.BooleanField')(default=1), keep_default=True)


    def backwards(self, orm):
        
        # Deleting field 'Submission.is_published'
        db.delete_column('challenges_submission', 'is_published')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'above_fold': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 19, 12, 40, 59, 781343)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'entrants_can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'sidebar': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 19, 12, 40, 59, 781183)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 5, 19, 12, 40, 59, 792065)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 19)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 5, 19)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = 0016_auto__add_field_submission_is_winner
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Submission.is_winner'
        db.add_column('challenges_submission', 'is_winner', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Submission.is_winner'
        db.delete_column('challenges_submission', 'is_winner')


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
        'challenges.challenge': {
            'Meta': {'object_name': 'Challenge'},
            'above_fold': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'allow_voting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'brief': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'challenges'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 7, 14, 9, 46, 30, 241393)', 'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateTimeField', [], {}),
            'entrants_can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'guidelines': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'important_dates': ('django.db.models.fields.TextField', [], {}),
            'is_open': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'resources': ('django.db.models.fields.TextField', [], {}),
            'rules': ('django.db.models.fields.TextField', [], {}),
            'sidebar': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 7, 14, 9, 46, 30, 241143)'}),
            'title': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'title_long': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'challenges.judge': {
            'Meta': {'unique_together': "(('challenge', 'user'),)", 'object_name': 'Judge'},
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['challenges.Challenge']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'judges'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.submission': {
            'Meta': {'object_name': 'Submission'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'challenge': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.Challenge']", 'symmetrical': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'submissions'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2011, 7, 14, 9, 46, 30, 260117)', 'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_winner': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'keywords': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.TextField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'challenges.voterdetails': {
            'Meta': {'object_name': 'VoterDetails'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'taxonomy': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['challenges.VoterTaxonomy']", 'symmetrical': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'voter_details'", 'to': "orm['users.UserProfile']"})
        },
        'challenges.votertaxonomy': {
            'Meta': {'object_name': 'VoterTaxonomy'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 7, 14)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 7, 14)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['challenges']

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
import logging
import bleach

from markdown import markdown

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import pre_save
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from drumbeat import storage
from drumbeat.utils import get_partition_id, safe_filename
from drumbeat.models import ModelBase

from projects.models import Project
from statuses.models import Status
from users.tasks import SendUserEmail

import caching.base

TAGS = ('h1', 'h2', 'a', 'b', 'em', 'i', 'strong',
        'ol', 'ul', 'li', 'hr', 'blockquote', 'p',
        'span', 'pre', 'code', 'img')

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt'],
}

log = logging.getLogger(__name__)


def determine_image_upload_path(instance, filename):
    return "images/challenges/%(partition)d/%(filename)s" % {
        'partition': get_partition_id(instance.pk),
        'filename': safe_filename(filename),
    }


class ChallengeManager(caching.base.CachingManager):
    def active(self, project_id=0):
        q = Challenge.objects.filter(
            start_date__lte=datetime.now()).filter(
            end_date__gte=datetime.now())
        if project_id:
            q = q.filter(project__id=project_id)
        return q

    def upcoming(self, project_id=0):
        q = Challenge.objects.filter(
            end_date__gte=datetime.now())
        if project_id:
            q = q.filter(project__id=project_id)
        return q


class Challenge(ModelBase):
    """ Inovation (design) Challenges """
    title = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    title_long = models.CharField(max_length=255)
    brief = models.TextField()
    guidelines = models.TextField()
    important_dates = models.TextField()
    resources = models.TextField()
    rules = models.TextField()

    sidebar = models.TextField(null=True, blank=True)
    above_fold = models.TextField(null=True, blank=True)

    start_date = models.DateTimeField(default=datetime.now())
    end_date = models.DateTimeField()

    image = models.ImageField(upload_to=determine_image_upload_path, null=True,
                              storage=storage.ImageStorage(), blank=True)

    project = models.ForeignKey(Project)
    created_by = models.ForeignKey('users.UserProfile',
                                   related_name='challenges')
    created_on = models.DateTimeField(auto_now_add=True,
                                      default=datetime.now())

    is_open = models.BooleanField()
    allow_voting = models.BooleanField(default=False)
    entrants_can_edit = models.BooleanField(default=True)

    objects = ChallengeManager()

    def get_winners(self):
        winners = self.submission_set.filter(is_winner=True)
        return {
            'winners':winners
        }
    
    def is_active(self):
        return (self.start_date < datetime.now() and
                self.end_date > datetime.now())

    @models.permalink
    def get_absolute_url(self):
        return ('challenges_show', (), {
            'slug': self.slug,
        })

    def __unicode__(self):
        return u"%s (%s - %s)" % (
            self.title,
            datetime.strftime(self.start_date, "%b %d %Y"),
            datetime.strftime(self.end_date, "%b %d %Y"))

    def save(self):
        """Make sure each challenge has a unique slug."""
        count = 1
        if not self.slug:
            slug = slugify(self.title)
            self.slug = slug
            while True:
                existing = Challenge.objects.filter(slug=self.slug)
                if len(existing) == 0:
                    break
                self.slug = slug + str(count)
                count += 1
        super(Challenge, self).save()
admin.site.register(Challenge)


class Submission(ModelBase):
    """ A submitted entry for a Challenge."""
    title = models.CharField(max_length=100)
    summary = models.TextField()
    description = models.TextField(null=True, blank=True)
    description_html = models.TextField(null=True, blank=True)

    keywords = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    challenge = models.ManyToManyField(Challenge)
    created_by = models.ForeignKey('users.UserProfile',
                                   related_name='submissions')
    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.now())

    is_published = models.BooleanField(default=True)

    is_winner = models.BooleanField(default=False)

    def get_challenge(self):
        challenges = self.challenge.all()
        if challenges:
            return challenges[0]
        else:
            return None

    def publish(self):
        self.is_published = True
        self.save()

        challenge = self.get_challenge()

        # Create activity
        msg = '<a href="%s">%s</a>: %s | <a href="%s">Read more</a>' % (
            challenge.get_absolute_url(), challenge.title, self.title,
            self.get_absolute_url())
        status = Status(author=self.created_by,
                        project=challenge.project,
                        status=msg)
        status.save()

        # Send thanks email
        user = self.created_by
        share_url = reverse('submission_edit_share', kwargs={
            'slug': challenge.slug,
            'submission_id': self.pk
        })
        submission_url = reverse('submission_show', kwargs={
            'slug': challenge.slug,
            'submission_id': self.pk
        })
        subj = _('Thanks for entering in the Knight-Mozilla Innovation Challenge!')
        body = render_to_string('challenges/emails/submission_thanks.txt', {
            'share_url': share_url,
            'submission_url': submission_url,
        })

        SendUserEmail.apply_async((user, subj, body))

    @models.permalink
    def get_absolute_url(self):
        challenge = self.get_challenge()
        if challenge:
            slug = challenge.slug
        else:
            slug = 'foo'  # TODO - Figure out what to do if no challenges exist
        return ('submission_show', (), {
            'slug': slug,
            'submission_id': self.id,
        })

    def __unicode__(self):
        return u"%s - %s" % (self.title, self.summary)

admin.site.register(Submission)


class VoterTaxonomy(ModelBase):
    description = models.CharField(max_length=255)

    def __unicode__(self):
        return self.description

admin.site.register(VoterTaxonomy)


class VoterDetails(ModelBase):
    user = models.ForeignKey('users.UserProfile',
                             related_name='voter_details')
    taxonomy = models.ManyToManyField(VoterTaxonomy)


class Judge(ModelBase):
    challenge = models.ForeignKey(Challenge)
    user = models.ForeignKey('users.UserProfile',
                             related_name='judges')

    class Meta:
        unique_together = (('challenge', 'user'),)


admin.site.register(Judge)


### Signals

def submission_markdown_handler(sender, **kwargs):
    submission = kwargs.get('instance', None)
    if not isinstance(submission, Submission):
        return
    if submission.description:
        submission.description_html = bleach.clean(
            markdown(submission.description),
            tags=TAGS, attributes=ALLOWED_ATTRIBUTES)
pre_save.connect(submission_markdown_handler, sender=Submission)

########NEW FILE########
__FILENAME__ = challenge_images
from BeautifulSoup import BeautifulSoup

from django import template

register = template.Library()

@register.inclusion_tag('challenges/images.html')
def challenge_images(haystack):

    images = []
    soup = BeautifulSoup(haystack)
    all_images = soup.findAll('img')

    for i in all_images:
        data = {
            'src':i,
            'url':i['src']
        }
        
        images.append(data)
    
    if len(images) != 0:
        return {
            'images':images
        }
    else:
        return {
            'images': False
        }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url, include
from models import Submission
from challenges.feeds import (ChallengesFeed, ProjectChallengesFeed,
                              SubmissionsFeed)
from voting.views import vote_on_object

vote_dict = {
  'model': Submission,
  'template_object_name': 'submission',
  'allow_xmlhttprequest': True,
}

urlpatterns = patterns('',
  # Challenges
  url(r'^create/project/(?P<project_id>\d+)/$',
      'challenges.views.create_challenge',
      name='challenges_create'),
  url(r'^(?P<slug>[\w-]+)/edit/$', 'challenges.views.edit_challenge',
      name='challenges_edit'),
  url(r'^(?P<slug>[\w-]+)/edit/image/$',
      'challenges.views.edit_challenge_image',
      name='challenges_edit_image'),
  url(r'^(?P<slug>[\w-]+)/edit/image/async$',
      'challenges.views.edit_challenge_image_async',
      name='challenges_edit_image_async'),

  url(r'^(?P<challenge>[\w-]+)/submissions/feed/$', SubmissionsFeed(),
      name='challenges_submissions_feed'),
  url(r'^(?P<project>[\w-]+)/feed/$', ProjectChallengesFeed(),
      name='challenges_project_feed'),
  url(r'^feed/$', ChallengesFeed(), name='challenges_feed'),

  url(r'^(?P<slug>[\w-]+)/$', 'challenges.views.show_challenge_winners',
      name='challenges_show'),
  url(r'^(?P<slug>[\w-]+)/all_ideas/$', 'challenges.views.show_all_submissions',
  name='all_submissions'),
  url(r'^(?P<slug>[\w-]+)/full$', 'challenges.views.show_challenge_full',
      name='challenges_show_full'),
  url(r'^(?P<slug>[\w-]+)/contact$', 'challenges.views.contact_entrants',
      name='challenges_contact_entrants'),

  # Submissions
  url(r'^(?P<slug>[\w-]+)/submission/create/$',
      'challenges.views.create_submission',
      name='submissions_create'),
  url(r'^(?P<slug>[\w-]+)/submission/(?P<submission_id>\d+)/$',
      'challenges.views.show_submission',
      name='submission_show'),
  url(r'^(?P<slug>[\w-]+)/submission/(?P<submission_id>\d+)/edit/$',
      'challenges.views.edit_submission',
      name='submission_edit'),
  url(r'^(?P<slug>[\w-]+)/submission/(?P<submission_id>\d+)/edit/desc/$',
      'challenges.views.edit_submission_description',
      name='submission_edit_description'),
  url(r'^(?P<slug>[\w-]+)/submission/(?P<submission_id>\d+)/edit/share/$',
      'challenges.views.edit_submission_share',
      name='submission_edit_share'),
  url(r'^(?P<slug>[\w-]+)/submission/(?P<submission_id>\d+)/delete/$',
      'challenges.views.delete_submission', name='submission_delete'),

  # Voting
  url(r'^(?P<slug>[\w-]+)/voting/get_more/$',
      'challenges.views.voting_get_more', name='challenge_voting_get_more'),
  url(r'^submission/(?P<object_id>\d+)/(?P<direction>up|clear)vote/?$',
      vote_on_object, vote_dict, name='submission_vote'),
  url(r'^submission/(?P<submission_id>\d+)/voter_details/',
      'challenges.views.submissions_voter_details',
      name='submissions_voter_details'),

  # Judges
  url(r'^(?P<slug>[\w-]+)/judges/$', 'challenges.views.challenge_judges',
      name='challenges_judges'),
  url(r'^(?P<slug>[\w-]+)/judges/delete/(?P<judge>[\d]+)/$',
      'challenges.views.challenge_judges_delete',
      name='challenges_judge_delete'),

  (r'^comments/', include('django.contrib.comments.urls')),
)

########NEW FILE########
__FILENAME__ = views
from datetime import datetime
import logging

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.utils import IntegrityError
from django.http import (HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden, Http404)
from django.shortcuts import get_object_or_404, render_to_response
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.template import RequestContext
from django.template.defaultfilters import truncatewords
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from commonware.decorators import xframe_sameorigin

from challenges.models import Challenge, Submission, Judge, VoterDetails
from challenges.forms import (ChallengeForm, ChallengeImageForm,
                              ChallengeContactForm,
                              SubmissionSummaryForm, SubmissionForm,
                              SubmissionDescriptionForm,
                              JudgeForm, VoterDetailsForm)
from challenges.decorators import (challenge_owner_required,
                                   submission_owner_required)
from projects.models import Project

from drumbeat import messages
from users.decorators import login_required
from voting.models import Vote

log = logging.getLogger(__name__)


@login_required
def create_challenge(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if project.slug != 'mojo':
        return HttpResponseForbidden()

    user = request.user.get_profile()

    if request.method == 'POST':
        form = ChallengeForm(request.POST)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.created_by = user
            challenge.project = project
            challenge.save()

            messages.success(request,
                             _('Your new challenge has been created.'))
            return HttpResponseRedirect(reverse('challenges_show', kwargs={
                'slug': challenge.slug,
                }))
        else:
            messages.error(request, _('Unable to create your challenge.'))
    else:
        form = ChallengeForm()

    context = {
        'form': form,
        'project': project,
    }
    return render_to_response('challenges/challenge_edit_summary.html',
                              context,
                              context_instance=RequestContext(request))


@login_required
@challenge_owner_required
def edit_challenge(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)
    user = request.user.get_profile()

    if user != challenge.created_by:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = ChallengeForm(request.POST, instance=challenge)
        if form.is_valid():
            form.save()
            messages.success(request, _('Challenge updated!'))
            return HttpResponseRedirect(reverse('challenges_show', kwargs={
                'slug': challenge.slug,
                }))
        else:
            messages.error(request, _('Unable to update your challenge.'))
    else:
        form = ChallengeForm(instance=challenge)

    context = {
        'form': form,
        'project': challenge.project,
        'challenge': challenge,
    }

    return render_to_response('challenges/challenge_edit_summary.html',
                              context,
                              context_instance=RequestContext(request))


@login_required
@xframe_sameorigin
@require_http_methods(['POST'])
@challenge_owner_required
def edit_challenge_image_async(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)
    form = ChallengeImageForm(request.POST, request.FILES, instance=challenge)
    if form.is_valid():
        instance = form.save()
        return HttpResponse(simplejson.dumps({
            'filename': instance.image.name,
        }))
    return HttpResponse(simplejson.dumps({
        'error': _('There was an error uploading your image.'),
    }))


@login_required
@challenge_owner_required
def edit_challenge_image(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    if request.method == "POST":
        form = ChallengeImageForm(
            request.POST, request.FILES, instance=challenge)
        if form.is_valid():
            messages.success(request, _('Challenge image updated'))
            form.save()
            return HttpResponseRedirect(
                reverse('challenges_edit_image', kwargs={
                    'slug': challenge.slug,
                }))
        else:
            messages.error(request,
                           _('There was an error uploading your image'))
    else:
        form = ChallengeImageForm(instance=challenge)

    context = {
        'form': form,
        'challenge': challenge,
    }

    return render_to_response('challenges/challenge_edit_image.html', context,
                              context_instance=RequestContext(request))


def show_challenge_winners(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    order = '?'
    
    submission_set = challenge.submission_set.filter(is_winner=True).extra(
        order_by=[order]
    )

    try:
        profile = request.user.get_profile()
    except:
        profile = None

    context = {
        'challenge': challenge,
        'submissions': submission_set,
        'profile': profile,
        'full_data': 'false'
    }

    return render_to_response('challenges/challenge_winners.html', context,
                              context_instance=RequestContext(request))

def show_challenge(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    qn = connection.ops.quote_name
    ctype = ContentType.objects.get_for_model(Submission)

    nsubmissions = challenge.submission_set.count()

    if challenge.allow_voting:
        order = '?'
    else:
        order = '-created_on'
    
    submission_set = challenge.submission_set.filter(is_published=True).extra(
        select={'score': """
        SELECT SUM(vote)
        FROM %s
        WHERE content_type_id = %s
        AND object_id = %s.id
        """ % (qn(Vote._meta.db_table), ctype.id,
               qn(Submission._meta.db_table))
        },
        order_by=[order]
    )

    if challenge.allow_voting:
        paginator = Paginator(submission_set, 4)
        tmpl = 'challenges/challenge_voting.html'
    else:
        paginator = Paginator(submission_set, 10)
        tmpl = 'challenges/challenge.html'

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        submissions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        submissions = paginator.page(paginator.num_pages)

    form = SubmissionSummaryForm()
    remaining = challenge.end_date - datetime.now()

    try:
        profile = request.user.get_profile()
    except:
        profile = None

    context = {
        'challenge': challenge,
        'submissions': submissions,
        'nsubmissions': nsubmissions,
        'form': form,
        'profile': profile,
        'remaining': remaining,
        'full_data': 'false'
    }

    return render_to_response(tmpl, context,
                              context_instance=RequestContext(request))


def show_all_submissions(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    qn = connection.ops.quote_name
    ctype = ContentType.objects.get_for_model(Submission)

    submission_set = challenge.submission_set.filter(
        is_published=True).extra(select={'score': """
        SELECT SUM(vote)
        FROM %s
        WHERE content_type_id = %s
        AND object_id = %s.id
        """ % (qn(Vote._meta.db_table), ctype.id,
               qn(Submission._meta.db_table))
        },
        order_by=['-created_on']
    )
    paginator = Paginator(submission_set, 10)

    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    try:
        submissions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        submissions = paginator.page(paginator.num_pages)

    form = SubmissionSummaryForm()
    remaining = challenge.end_date - datetime.now()

    try:
        profile = request.user.get_profile()
    except:
        profile = None

    context = {
        'challenge': challenge,
        'submissions': submissions,
        'form': form,
        'profile': profile,
        'remaining': remaining
    }

    return render_to_response('challenges/all_submissions.html', context,
                              context_instance=RequestContext(request))


def show_challenge_full(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    context = {
        'challenge': challenge,
    }

    return render_to_response('challenges/challenge_full.html', context,
                              context_instance=RequestContext(request))


@login_required
@challenge_owner_required
def contact_entrants(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)
    if request.method == 'POST':
        form = ChallengeContactForm(request.POST)
        if form.is_valid():
            form.save(sender=request.user)
            messages.info(request, _('Message sent successfully.'))
            return HttpResponseRedirect(reverse('challenges_show', kwargs={
                'slug': challenge.slug,
            }))
    else:
        form = ChallengeContactForm()
        form.fields['challenge'].initial = challenge.pk

    return render_to_response('challenges/contact_entrants.html', {
        'form': form,
        'challenge': challenge,
    }, context_instance=RequestContext(request))


def voting_get_more(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)
    if not challenge.allow_voting:
        return HttpResponseForbidden()

    count = request.GET.get('count', 1)
    exclude = request.GET.get('exclude', [])
    if exclude:
        exclude = exclude.split(',')

    submissions = challenge.submission_set.exclude(
        pk__in=exclude).order_by('?')[:count]

    try:
        profile = request.user.get_profile()
    except:
        profile = None

    response = []
    for submission in submissions:
        response.append(
            render_to_string('challenges/_voting_resource.html',
                             {'submission': submission,
                              'challenge': challenge,
                              'full_data': 'false',
                              'profile': profile},
                            context_instance=RequestContext(request)))

    return HttpResponse(simplejson.dumps({
        'submissions': response,
    }))


@login_required
def create_submission(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)
    if not challenge.is_active():
        return HttpResponseForbidden()

    user = request.user.get_profile()

    if request.method == 'POST':
        truncate_title = lambda s: truncatewords(s, 10)[:90]
        post_data = request.POST.copy()
        post_data['title'] = truncate_title(post_data['summary'])
        form = SubmissionForm(post_data)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.title = truncate_title(submission.summary)
            submission.created_by = user
            submission.is_published = False
            submission.save()

            submission.challenge.add(challenge)

            messages.success(request, _('Your submission has been created'))
            return HttpResponseRedirect(reverse('submission_edit', kwargs={
                'slug': challenge.slug,
                'submission_id': submission.pk,
                }))
        else:
            messages.error(request, _('Unable to create your submission'))
    else:
        form = SubmissionForm()

    context = {
        'form': form,
        'challenge': challenge,
    }

    return render_to_response('challenges/submission_edit.html', context,
                              context_instance=RequestContext(request))


@login_required
@submission_owner_required
def edit_submission(request, slug, submission_id):
    challenge = get_object_or_404(Challenge, slug=slug)
    if not challenge.entrants_can_edit:
        return HttpResponseForbidden()

    try:
        submission = challenge.submission_set.get(pk=submission_id)
    except:
        raise Http404

    if request.method == 'POST':
        form = SubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            submission = form.save()
            messages.success(request, _('Your submission has been edited.'))

            if 'publish' in request.POST:
                submission.publish()

            return HttpResponseRedirect(reverse('submission_edit_description',
                kwargs={
                    'slug': challenge.slug,
                    'submission_id': submission.pk,
            }))
        else:
            messages.error(request, _('Unable to update your submission'))
    else:
        form = SubmissionForm(instance=submission)

    ctx = {
        'challenge': challenge,
        'submission': submission,
        'form': form,
    }

    return render_to_response('challenges/submission_edit_summary.html',
                              ctx, context_instance=RequestContext(request))


@login_required
@submission_owner_required
def edit_submission_description(request, slug, submission_id):
    challenge = get_object_or_404(Challenge, slug=slug)
    if not challenge.entrants_can_edit:
        return HttpResponseForbidden()

    try:
        submission = challenge.submission_set.get(pk=submission_id)
    except:
        raise Http404

    if request.method == 'POST':
        form = SubmissionDescriptionForm(request.POST, instance=submission)
        if form.is_valid():
            submission = form.save()
            messages.success(request, _('Your submission has been edited.'))

            if 'publish' in request.POST:
                submission.publish()

            return HttpResponseRedirect(reverse('submission_edit_share',
                kwargs={
                    'slug': challenge.slug,
                    'submission_id': submission.pk
            }))
        else:
            messages.error(request, _('Unable to update your submission'))
    else:
        form = SubmissionDescriptionForm(instance=submission)

    ctx = {
        'challenge': challenge,
        'submission': submission,
        'form': form
    }

    return render_to_response('challenges/submission_edit_description.html',
                              ctx, context_instance=RequestContext(request))


@login_required
@submission_owner_required
def edit_submission_share(request, slug, submission_id):
    challenge = get_object_or_404(Challenge, slug=slug)
    try:
        submission = challenge.submission_set.get(pk=submission_id)
    except:
        raise Http404

    url = request.build_absolute_uri(reverse('submission_show', kwargs={
        'slug': challenge.slug, 'submission_id': submission.pk
    }))

    ctx = {
        'challenge': challenge,
        'submission': submission,
        'url': url,
    }

    return render_to_response('challenges/submission_edit_share.html',
                              ctx, context_instance=RequestContext(request))


@login_required
@submission_owner_required
def delete_submission(request, slug, submission_id):
    challenge = get_object_or_404(Challenge, slug=slug)
    try:
        submission = challenge.submission_set.get(pk=submission_id)
    except:
        raise Http404

    if request.method == 'POST':
        post_data = request.POST.copy()
        if post_data['confirm']:
            submission.delete()
            messages.success(request, _('Your submission has been deleted'))

            return HttpResponseRedirect(reverse('challenges_show',
                kwargs={'slug': challenge.slug}))
        else:
            messages.error(request, _('Unable to delete submission'))

    context = {
        'challenge': challenge,
        'submission': submission
    }

    return render_to_response('challenges/delete_confirm.html', context,
                              context_instance=RequestContext(request))


def show_submission(request, slug, submission_id):
    challenge = get_object_or_404(Challenge, slug=slug)
    try:
        submission = challenge.submission_set.get(pk=submission_id)
    except:
        raise Http404

    if not submission.is_published:
        if not request.user.is_authenticated():
            raise Http404
        user = request.user.get_profile()
        if user != submission.created_by:
            raise Http404

    context = {
        'challenge': challenge,
        'submission': submission,
    }

    return render_to_response('challenges/submission_show.html', context,
                              context_instance=RequestContext(request))


@login_required
@challenge_owner_required
def challenge_judges(request, slug):
    challenge = get_object_or_404(Challenge, slug=slug)

    if request.method == 'POST':
        form = JudgeForm(request.POST)
        if form.is_valid():
            judge = form.save(commit=False)
            judge.challenge = challenge

            try:
                judge.save()
                messages.success(request, _('Judge has been added'))
            except IntegrityError:
                messages.error(request, _('User is already a judge'))

            return HttpResponseRedirect(reverse('challenges_judges', kwargs={
                'slug': challenge.slug,
            }))
        else:
            messages.error(request, _('Unable to add judge.'))
    else:
        form = JudgeForm()

    judges = Judge.objects.filter(challenge=challenge)

    context = {
        'challenge': challenge,
        'form': form,
        'judges': judges,
    }

    return render_to_response('challenges/challenge_judges.html', context,
                              context_instance=RequestContext(request))


@login_required
@challenge_owner_required
def challenge_judges_delete(request, slug, judge):
    if request.method == 'POST':
        challenge = get_object_or_404(Challenge, slug=slug)
        judge = get_object_or_404(Judge, pk=judge)
        if judge.challenge != challenge:
            return HttpResponseForbidden()
        judge.delete()
        messages.success(request, _('Judge removed.'))
    return HttpResponseRedirect(reverse('challenges_judges', kwargs={
        'slug': challenge.slug,
    }))


@login_required
def submissions_voter_details(request, submission_id):
    submission = get_object_or_404(Submission, pk=submission_id)

    try:
        voter = VoterDetails.objects.get(user=request.user.get_profile())
    except:
        voter = None

    if request.method == 'POST':
        form = VoterDetailsForm(request.POST, instance=voter)
        if form.is_valid():
            details = form.save(commit=False)
            details.user = request.user.get_profile()
            details.save()
            form.save_m2m()

            messages.success(request, _('Your details were saved.'))

            return HttpResponseRedirect(reverse('challenges_show', kwargs={
                'slug': submission.challenge.get().slug,
            }))
        else:
            messages.error(request, _('Unable to save details'))
    else:
        form = VoterDetailsForm(instance=voter)
    context = {
        'form': form,
        'submission': submission,
    }

    return render_to_response('challenges/voter_details.html', context,
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FeedEntry'
        db.create_table('dashboard_feedentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('checksum', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('dashboard', ['FeedEntry'])


    def backwards(self, orm):
        
        # Deleting model 'FeedEntry'
        db.delete_table('dashboard_feedentry')


    models = {
        'dashboard.feedentry': {
            'Meta': {'object_name': 'FeedEntry'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'checksum': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = 0002_auto__drop_feedentry
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Drop table 'dashboard_feedentry'
        db.delete_table('dashboard_feedentry', cascade=False)

    def backwards(self, orm):
        # Adding model 'FeedEntry'
        db.create_table('dashboard_feedentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('checksum', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('dashboard', ['FeedEntry'])

    models = {
        'dashboard.feedentry': {
            'Meta': {'object_name': 'FeedEntry'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'checksum': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['dashboard']

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User
from django.test import Client
from test_utils import TestCase

from users.models import UserProfile


class DashboardTests(TestCase):

    test_username = 'testuser'
    test_password = 'testpassword'
    test_email = 'test@mozillafoundation.org'

    def setUp(self):
        self.locale = 'en-US'
        self.client = Client()
        self.user = User.objects.create_user(self.test_username,
                                             self.test_email,
                                             self.test_password)

    def test_unauthorized_request(self):
        """Unauthorized requests should get a signin template."""
        response = self.client.get('/%s/' % (self.locale,))
        self.assertTemplateUsed(response, 'dashboard/splash.html')

    def test_authorized_request_no_profile(self):
        """
        Authorized requests without a user profile should default to
        setup profile page.
        """
        self.client.login(username=self.test_username,
                          password=self.test_password)
        response = self.client.get('/%s/' % (self.locale,))
        self.assertTemplateUsed(response, 'dashboard/setup_profile.html')

    def test_authorized_request_profile(self):
        """
        Test that an authorized request with a user profile lands on
        a personalized dashboard page.
        """
        user = UserProfile(
            username=self.test_username,
            email=self.test_email,
            user=self.user)
        user.save()
        self.client.login(username=self.test_username,
                          password=self.test_password)
        response = self.client.get('/%s/' % (self.locale,))
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'dashboard.views.index', name='dashboard_index'),
    url(r'^broadcasts/hide_welcome/$', 'dashboard.views.hide_welcome',
        name='dashboard_hide_welcome'),
)

########NEW FILE########
__FILENAME__ = views
import random

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt

from activity.models import Activity
from users.decorators import anonymous_only, login_required
from users.models import UserProfile
from users.forms import CreateProfileForm
from projects.models import Project
from relationships.models import Relationship


@anonymous_only
def splash(request):
    """Splash page we show to users who are not authenticated."""
    project = None
    projects = Project.objects.filter(featured=True)
    if projects:
        project = random.choice(projects)
        project.followers_count = Relationship.objects.filter(
            target_project=project).count()
    activities = Activity.objects.public()
    feed_url = getattr(settings, 'SPLASH_PAGE_FEED', None)
    return render_to_response('dashboard/splash.html', {
        'activities': activities,
        'featured_project': project,
        'feed_url': feed_url,
    }, context_instance=RequestContext(request))


@login_required
@csrf_exempt
def hide_welcome(request):
    profile = request.user.get_profile()
    if not profile.discard_welcome:
        profile.discard_welcome = True
        profile.save()
    if request.is_ajax():
        return HttpResponse()
    return HttpResponseRedirect(reverse('dashboard_index'))


@login_required(profile_required=False)
def dashboard(request):
    """Personalized dashboard for authenticated users."""
    try:
        profile = request.user.get_profile()
    except UserProfile.DoesNotExist:
        user = request.user
        username = ''
        if user.username[:10] != 'openiduser':
            username = user.username
        form = CreateProfileForm(initial={
            'display_name': ' '.join((user.first_name, user.last_name)),
            'email': user.email,
            'username': username,
        })
        return render_to_response('dashboard/setup_profile.html', {
            'form': form,
        }, context_instance=RequestContext(request))
    projects_following = profile.following(model=Project)
    users_following = profile.following()
    users_followers = profile.followers()
    activities = Activity.objects.dashboard(request.user.get_profile())
    user_projects = Project.objects.filter(created_by=profile)
    show_welcome = not profile.discard_welcome
    return render_to_response('dashboard/dashboard.html', {
        'users_following': users_following,
        'users_followers': users_followers,
        'projects_following': projects_following,
        'activities': activities,
        'projects': user_projects,
        'show_welcome': show_welcome,
    }, context_instance=RequestContext(request))


def index(request):
    """
    Direct user to personalized dashboard or generic splash page, depending
    on whether they are logged in authenticated or not.
    """
    if request.user.is_authenticated():
        return dashboard(request)
    return splash(request)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def django_conf(request):
    return {'settings': settings}

########NEW FILE########
__FILENAME__ = forms
from django import forms


class AbuseForm(forms.Form):
    pass

########NEW FILE########
__FILENAME__ = messages
from django.contrib import messages as django_messages
from django.template.loader import render_to_string

# Idea taken from Zamboni. Wrap functions in the Django messages contrib
# application so we can mark certain messages safe and insert HTML.


def _make_message(message, safe=False):
    c = {'message': message, 'safe': safe}
    return render_to_string('drumbeat/message_content.html', c)


def info(request, message, extra_tags='', fail_silently=False, safe=False):
    msg = _make_message(message, safe)
    django_messages.info(request, msg, extra_tags, fail_silently)


def debug(request, message, extra_tags='', fail_silently=False, safe=False):
    msg = _make_message(message, safe)
    django_messages.debug(request, msg, extra_tags, fail_silently)


def success(request, message, extra_tags='', fail_silently=False, safe=False):
    msg = _make_message(message, safe)
    django_messages.success(request, msg, extra_tags, fail_silently)


def warning(request, message, extra_tags='', fail_silently=False, safe=False):
    msg = _make_message(message, safe)
    django_messages.warning(request, msg, extra_tags, fail_silently)


def error(request, message, extra_tags='', fail_silently=False, safe=False):
    msg = _make_message(message, safe)
    django_messages.error(request, msg, extra_tags, fail_silently)

########NEW FILE########
__FILENAME__ = models
from django.db import models

import caching.base


class ManagerBase(caching.base.CachingManager, models.Manager):
    pass


class ModelBase(caching.base.CachingMixin, models.Model):
    objects = caching.base.CachingManager()

    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = storage
import os
import Image
import logging

from django.core.files.storage import FileSystemStorage

log = logging.getLogger(__name__)


class ImageStorage(FileSystemStorage):

    format_extensions = {
        'PNG': 'png',
        'GIF': 'gif',
        'JPEG': 'jpg',
        'JPG': 'jpg',
    }

    def _save(self, name, content):
        name, ext = os.path.splitext(name)
        image = Image.open(content)
        if image.format in self.format_extensions:
            name = "%s.%s" % (name, self.format_extensions[image.format])
        else:
            log.warn("Attempt to upload image of unknown format: %s" % (
                image.format,))
            raise Exception("Unknown image format: %s" % (image.format,))
        name = super(ImageStorage, self)._save(name, content)
        image.save(self.path(name), image.format)
        return name

########NEW FILE########
__FILENAME__ = truncate_chars
# Taken from http://djangosnippets.org/snippets/1516/

from django.template import Library
from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy
from django.template.defaultfilters import stringfilter

register = Library()


def truncate_chars(s, num):
    """
    Template filter to truncate a string to at most num characters
    respecting word boundaries.
    """
    s = force_unicode(s)
    length = int(num)
    if len(s) > length:
        length = length - 3
        if s[length-1] == ' ' or s[length] == ' ':
            s = s[:length].strip()
        else:
            words = s[:length].split()
            if len(words) > 1:
                del words[-1]
            s = u' '.join(words)
        s += '...'
    return s
truncate_chars = allow_lazy(truncate_chars, unicode)


def truncatechars(value, arg):
    """
    Truncates a string after a certain number of characters, but respects word
    boundaries.

    Argument: Number of characters to truncate after.
    """
    try:
        length = int(arg)
    except ValueError: # If the argument is not a valid integer.
        return value # Fail silently.
    return truncate_chars(value, length)
truncatechars.is_safe = True
truncatechars = stringfilter(truncatechars)

register.filter(truncatechars)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponseRedirect


# mojo URLs - keep until mozillaopennews.org is going
urlpatterns = patterns('django.views.generic.simple',
    url(r'^journalism/participate/$', 'direct_to_template', {
        'template': 'drumbeat/journalism/participate.html',
   }, name='drumbeat_journalism_participate'),
   url(r'^journalism/process/$', 'direct_to_template', {
        'template': 'drumbeat/journalism/process.html',
   }, name='drumbeat_journalism_process'),
   url(r'^journalism/about/$', 'direct_to_template', {
        'template': 'drumbeat/journalism/about.html',
   }, name='drumbeat_journalism_about'),
   url(r'^journalism/learninglab/$', 'direct_to_template', {
        'template': 'drumbeat/journalism/learninglab.html',
   }, name='mojo_learning_lab')
)
urlpatterns += patterns('',
    url(r'^journalism/$',
       lambda x: HttpResponseRedirect('http://www.mozillaopennews.org/')),
    url(r'^journalism/2011/$',
       'drumbeat.views.journalism',
       name='drumbeat_journalism'),
    url(r'^journalism/challenges/$',
        'drumbeat.views.design_challenges',
        name='mojo_design_challenges'),
)

# URLs we want to retire
urlpatterns += patterns('',
   url(r'^terms-of-service/$', 'drumbeat.views.drumbeat_retired'
    , name='drumbeat_tos'),
   url(r'^about/$', 'drumbeat.views.drumbeat_retired'
    , name='drumbeat_about'),
   url(r'^editing-help/$', 'drumbeat.views.drumbeat_retired'
    , name='drumbeat_editing'),
   url(r'^abuse/(?P<type>[\w ]+)/(?P<obj>\w+)/$',
       'drumbeat.views.drumbeat_retired',
       name='drumbeat_abuse'),
)

########NEW FILE########
__FILENAME__ = utils
import os
import re
import math
import hashlib
import unicodedata

from django.core.validators import ValidationError, validate_slug
from django.utils.encoding import smart_unicode

# Some utility functions shamelessly lifted from zamboni

# Extra characters outside of alphanumerics that we'll allow.
SLUG_OK = '-_'


def slugify(s, ok=SLUG_OK, lower=True):
    # L and N signify letter/number.
    # http://www.unicode.org/reports/tr44/tr44-4.html#GC_Values_Table
    rv = []
    for c in smart_unicode(s):
        cat = unicodedata.category(c)[0]
        if cat in 'LN' or c in ok:
            rv.append(c)
        if cat == 'Z':  # space
            rv.append(' ')
    new = re.sub('[-\s]+', '-', ''.join(rv).strip())
    return new.lower() if lower else new


def slug_validator(s, ok=SLUG_OK, lower=True):
    """
    Raise an error if the string has any punctuation characters.

    Regexes don't work here because they won't check alnums in the right
    locale.
    """
    if not (s and slugify(s, ok, lower) == s):
        raise ValidationError(validate_slug.message,
                              code=validate_slug.code)


def get_partition_id(pk, chunk_size=1000):
    """
    Given a primary key and optionally the number of models that will get
    shared access to a directory, return an integer representing a directory
    name.
    """
    return int(math.ceil(pk / float(chunk_size)))


def safe_filename(filename):
    """Generate a safe filename for storage."""
    name, ext = os.path.splitext(filename)
    return "%s%s" % (hashlib.md5(name.encode('utf8')).hexdigest(), ext)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django import http
from django.template import RequestContext, Context, loader
from django.shortcuts import render_to_response

from challenges.models import Challenge, Submission
from feeds.models import FeedEntry
from users.models import UserProfile
from users.tasks import SendUserEmail
from drumbeat.forms import AbuseForm


def drumbeat_retired(request):
    """ Send all request to the homepage """
    return http.HttpResponseRedirect('/')

def server_error(request):
    """Make MEDIA_URL available to the 500 template."""
    t = loader.get_template('500.html')
    return http.HttpResponseServerError(t.render(Context({
        'MEDIA_URL': settings.MEDIA_URL,
    })))


def report_abuse(request, obj, type):
    """Report abusive or irrelavent content."""
    if request.method == 'POST':
        # we only use the form for the csrf middleware. skip validation.
        form = AbuseForm(request.POST)
        body = """
        User %s has reported the following content as objectionable:

        Model: %s, ID: %s
        """ % (request.user.get_profile().name, type, obj)
        subject = "Abuse Report"
        try:
            profile = UserProfile.objects.get(email=settings.ADMINS[0][1])
            SendUserEmail.apply_async(args=(profile, subject, body))
        except:
            pass
        return render_to_response('drumbeat/report_received.html', {},
                                  context_instance=RequestContext(request))
    else:
        form = AbuseForm()
    return render_to_response('drumbeat/report_abuse.html', {
        'form': form,
        'obj': obj,
        'type': type,
    }, context_instance=RequestContext(request))


def journalism(request):
    feed_entries = FeedEntry.objects.filter(
        page='mojo').order_by('-created_on')[0:4]
    feed_url = getattr(settings, 'FEED_URLS', None)
    if feed_url and 'mojo' in feed_url:
        feed_url = feed_url['mojo']
    slugs = ('open-webs-killer-app', 'beyond-comment-threads',
             'unlocking-video')
    counts = {}
    for slug in slugs:
        challenge = Challenge.objects.get(slug=slug)
        key = slug.replace('-', '')
        counts[key] = Submission.objects.filter(challenge=challenge).count()
    return render_to_response('drumbeat/journalism/index.html', {
        'feed_entries': feed_entries,
        'feed_url': feed_url,
        'counts': counts,
    }, context_instance=RequestContext(request))

def design_challenges(request):
    challenges = []
    slugs = ('open-webs-killer-app', 'beyond-comment-threads', 'unlocking-video')
    for slug in slugs:
        challenge = Challenge.objects.get(slug=slug)
        challenges.append(challenge)
    return render_to_response('drumbeat/journalism/challenges.html', {
       'challenges': challenges, 
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from users.models import UserProfile


class UserField(forms.Field):
    widget = forms.widgets.TextInput

    def clean(self, value):
        super(UserField, self).clean(value)
        if not value:
            return ''
        try:
            profile = UserProfile.objects.get(
                Q(username=value) |
                Q(email=value),
            )
        except UserProfile.DoesNotExist:
            raise forms.ValidationError(
                _(u'No such user with that username or email.'))

        # we return a list of ``User`` objects because that's what
        # the pinax messages application expects.
        return [profile.user]

########NEW FILE########
__FILENAME__ = forms
import logging

from messages.forms import ComposeForm as MessagesComposeForm

from drumbeatmail.fields import UserField

log = logging.getLogger(__name__)


class ComposeForm(MessagesComposeForm):
    recipient = UserField()

    def __init__(self, sender=None, *args, **kwargs):
        self.sender = sender
        super(ComposeForm, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

from messages.models import Message
from users.tasks import SendUserEmail
from preferences.models import AccountPreferences

import logging

log = logging.getLogger(__name__)


def message_sent_handler(sender, **kwargs):
    message = kwargs.get('instance', None)
    if not isinstance(message, Message):
        return
    user = message.recipient
    preferences = AccountPreferences.objects.filter(
        user=user.get_profile())
    for preference in preferences:
        if preference.value and preference.key == 'no_email_message_received':
            return
    sender = message.sender.get_profile().name
    subject = _('New Message from %(name)s' % {
        'name': sender,
    })
    body = render_to_string('drumbeatmail/emails/direct_message.txt', {
        'sender': sender,
        'message': message.body,
        'reply_url': reverse('drumbeatmail_reply', kwargs={
            'message': message.pk,
        }),
    })
    SendUserEmail.apply_async((user.get_profile(), subject, body))
post_save.connect(message_sent_handler, sender=Message)

########NEW FILE########
__FILENAME__ = tests
from users.models import UserProfile
from drumbeatmail.forms import ComposeForm
from relationships.models import Relationship
from projects.models import Project
from messages.models import Message

import test_utils


class TestDrumbeatMail(test_utils.TestCase):

    test_username = 'testuser'
    test_password = 'testpassword'
    test_email = 'test@mozillafoundation.org'

    def setUp(self):
        self.locale = 'en-US'
        self.user = UserProfile(username=self.test_username,
                                email=self.test_email)
        self.user.set_password(self.test_password)
        self.user.save()
        self.user.create_django_user()

        self.user_two = UserProfile(username='anotheruser',
                               email='test2@mozillafoundation.org')
        self.user_two.set_password('testpassword')
        self.user_two.save()
        self.user_two.create_django_user()

    def test_messaging_user_following(self):
        print "From test: %s" % (self.user.user,)
        print "From test: %s" % (self.user_two.user,)
        Relationship(source=self.user_two, target_user=self.user).save()
        form = ComposeForm(data={
            'recipient': self.user_two,
            'subject': 'Foo',
            'body': 'Bar',
        }, sender=self.user)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.is_valid())

    def test_messaging_user_following_project(self):
        project = Project(
            name='test project',
            short_description='abcd',
            long_description='edfgh',
            created_by=self.user)
        project.save()
        Relationship(source=self.user_two, target_project=project).save()
        form = ComposeForm(data={
            'recipient': self.user_two,
            'subject': 'Foo',
            'body': 'Bar',
        }, sender=self.user)
        self.assertTrue(form.is_bound)
        self.assertTrue(form.is_valid())

    def test_view_message(self):
        """Test user can view message in inbox."""
        Relationship(source=self.user, target_user=self.user_two).save()
        message = Message(
            sender=self.user_two.user,
            recipient=self.user.user,
            subject='test message subject',
            body='test message body')
        message.save()
        self.client.login(username=self.test_username,
                          password=self.test_password)
        response = self.client.get("/%s/messages/inbox/" % (self.locale,))
        self.assertContains(response, 'test message body')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import redirect_to


urlpatterns = patterns('',
    url(r'^$', redirect_to, {'url': 'inbox/'}),
    url(r'^inbox/$', 'drumbeatmail.views.inbox',
        name='drumbeatmail_inbox'),
    url(r'^inbox/(?P<page_number>[\d]+)/$', 'drumbeatmail.views.inbox',
        name='drumbeatmail_inbox_offset'),
    url(r'^inbox/(?P<filter>[\w\-\. ]+)/$',
        'drumbeatmail.views.inbox_filtered',
        name='drumbeatmail_inbox_filtered'),
    url(r'^inbox/(?P<filter>[\w\-\. ]+)/(?P<page_number>[\d]+)/$',
        'drumbeatmail.views.inbox_filtered',
        name='drumbeatmail_inbox_filtered_offset'),
    url(r'^outbox/$', 'drumbeatmail.views.outbox',
        name='drumbeatmail_outbox'),
    url(r'^outbox/(?P<page_number>[\d]+)/$', 'drumbeatmail.views.outbox',
        name='drumbeatmail_outbox_offset'),
    url(r'^compose/$', 'drumbeatmail.views.compose',
        name='drumbeatmail_compose'),
    url(r'^(?P<username>[\w\-\. ]+)/$', 'drumbeatmail.views.compose',
        name='drumbeatmail_compose_to'),
    url(r'^reply/(?P<message>[\d]+)/$', 'drumbeatmail.views.reply',
        name='drumbeatmail_reply'),
)

########NEW FILE########
__FILENAME__ = views
import logging
import math
import datetime
import operator

from django import http
from django.db.models.fields.files import ImageFieldFile
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson
from django.utils.translation import ugettext as _

from drumbeat import messages
from drumbeatmail import forms
from messages.models import Message
from users.models import UserProfile
from users.decorators import login_required

log = logging.getLogger(__name__)

PAGE_SIZE = 10  # Number of messages to display on one page


def get_sorted_senders(user):
    """
    Helper function. Return a list of distinct senders, sorted by
    the number of messages received from them.
    """
    msgs = Message.objects.inbox_for(user).select_related('sender')
    senders = {}
    for msg in msgs:
        sender = msg.sender.get_profile()
        senders.setdefault(sender, 0)
        senders[sender] += 1
    return sorted(senders.iteritems(), key=operator.itemgetter(1))


def get_pagination_options(count, page_number):
    """
    Helper function. Calculate and return the number of pages and
    the start and end indices based on a total count and page number.
    """
    n_pages = int(math.ceil(count / float(PAGE_SIZE)))
    start = (page_number - 1) * PAGE_SIZE
    end = page_number * PAGE_SIZE
    return (n_pages, start, end)


def serialize(inbox, sent_view=False):
    """Serialize messages for xhr."""
    data = []
    for msg in inbox:
        sender = msg.sender
        if sent_view:
            sender = msg.recipient
        img = sender.get_profile().image_or_default()
        if isinstance(img, ImageFieldFile):
            img = img.name
        serialized = {
            'abuse_url': reverse('drumbeat_abuse', kwargs=dict(
                obj=msg.id, type='message')),
            'reply_url': reverse('drumbeatmail_reply', kwargs=dict(
                message=msg.id)),
            'sender_url': sender.get_profile().get_absolute_url(),
            'sender_img': img,
            'sender_name': sender.get_profile().name,
            'subject': msg.subject,
            'body': msg.body,
            'sent_at': msg.sent_at.strftime('%b. %d, %Y, %I:%M %p').replace(
                'PM', 'p.m.').replace('AM', 'a.m.'),
        }
        if sent_view:
            del serialized['abuse_url']
            del serialized['reply_url']
        data.append(serialized)
    return simplejson.dumps(data)


def generic_inbox(request, query_method, query_args, page_number,
                  more_link_name, more_link_kwargs, redirect, filter=None,
                  sent_view=False):
    """
    Three views in this application render the inbox with different but
    very similar contexts. This is a helper function used to wrap that
    rendering and all of the pagination logic.

    ``request`` - The ``HttpRequest`` object associated with this request.
    ``query_method`` - A callable that will return a list of messages for
                       this view.
    ``query_args`` - A list of arguments for ``query_method``.
    ``page_number`` - The page number being rendered.
    ``more_link_name`` - A named URLconf to use for the more link.
    ``more_link_kwargs`` - Named arguments for the more link.
    ``redirect`` - A URL to redirect to for invalid page numbers.
    ``filter`` - Optional filter kwargs for ``query_method``.
    ``sent_view`` - Whether or not to render the outbox view or not. When
                    viewing the outbox, user icons are the recipient, not
                    the sender.
    """
    page_number = int(page_number)
    msgs = query_method(*query_args)
    if filter:
        msgs = msgs.filter(**filter)
    count = msgs.count()
    (n_pages, start, end) = get_pagination_options(count, page_number)

    if n_pages > 0 and page_number > n_pages:
        return http.HttpResponseRedirect(redirect)

    inbox = msgs.select_related('sender')[start:end]
    senders = get_sorted_senders(request.user)

    for msg in inbox:
        if not msg.read_at:
            msg.read_at = datetime.datetime.now()
            msg.save()

    if request.is_ajax():
        data = serialize(inbox, sent_view)
        return http.HttpResponse(data, 'application/json')

    page_number += 1
    more_link_kwargs['page_number'] = page_number
    more_link = reverse(more_link_name, kwargs=more_link_kwargs)
    return render_to_response('drumbeatmail/inbox.html', {
        'inbox': inbox,
        'senders': senders,
        'page_number': page_number,
        'n_pages': n_pages,
        'more_link': more_link,
        'sent_view': sent_view,
    }, context_instance=RequestContext(request))


@login_required
def inbox(request, page_number=1):
    func = Message.objects.inbox_for
    func_args = (request.user,)
    more_link_name = 'drumbeatmail_inbox_offset'
    return generic_inbox(
        request, func, func_args, page_number, more_link_name, {},
        reverse('drumbeatmail_inbox'))


@login_required
def inbox_filtered(request, filter, page_number=1):
    sender = get_object_or_404(UserProfile, username=filter)
    func = Message.objects.inbox_for
    func_args = (request.user,)
    redirect_url = reverse('drumbeatmail_inbox_filtered',
                           kwargs=dict(filter=filter))
    more_link_name = 'drumbeatmail_inbox_filtered_offset'
    more_link_kwargs = dict(filter=filter)
    return generic_inbox(
        request, func, func_args, page_number, more_link_name,
        more_link_kwargs, redirect_url, dict(sender=sender))


@login_required
def outbox(request, page_number=1):
    func = Message.objects.outbox_for
    func_args = (request.user,)
    more_link_name = 'drumbeatmail_outbox_offset'
    return generic_inbox(
        request, func, func_args, page_number, more_link_name, {},
        reverse('drumbeatmail_outbox'), sent_view=True)


@login_required
def reply(request, message):
    message = get_object_or_404(Message, id=message)
    if message.recipient != request.user:
        return http.HttpResponseForbidden()
    if request.method == 'POST':
        form = forms.ComposeForm(data=request.POST,
                                 sender=request.user.get_profile())
        if form.is_valid():
            form.save(sender=request.user)
            messages.success(request, _('Message successfully sent.'))
            return http.HttpResponseRedirect(reverse('drumbeatmail_inbox'))
        else:
            messages.error(request, _('There was an error sending your message'
                                      '. Please try again.'))
    else:
        form = forms.ComposeForm(initial={
            'recipient': message.sender.get_profile().username,
            'subject': 'Re: %s' % (message.subject,),
        })
    return render_to_response('drumbeatmail/reply.html', {
        'form': form,
        'message': message,
    }, context_instance=RequestContext(request))


@login_required
def compose(request, username=None):
    kwargs = {}
    if username:
        kwargs['user'] = get_object_or_404(UserProfile, username=username)
    if request.method == 'POST':
        form = forms.ComposeForm(data=request.POST,
                                 sender=request.user.get_profile())
        if form.is_valid():
            form.save(sender=request.user)
            messages.success(request, _('Message successfully sent.'))
            return http.HttpResponseRedirect(reverse('drumbeatmail_inbox'))
        else:
            messages.error(request, _('There was an error sending your message'
                                      '. Please try again.'))
    else:
        form = forms.ComposeForm(initial={'recipient': username})
    kwargs['form'] = form
    return render_to_response('drumbeatmail/compose.html', kwargs,
                              context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
  url(r'^$', 'django.views.generic.simple.direct_to_template', {
      'template': 'events/index.html',
  }, name='events_index'),
)

########NEW FILE########
__FILENAME__ = context_processors
from feeds.models import FeedEntry

def feed_entries(request):
    feed_entries = FeedEntry.objects.filter(
        page='splash').order_by('-created_on')[0:3]

    return {
        'feed_entries': feed_entries
    }

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'FeedEntry'
        db.create_table('feeds_feedentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('link', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('body', self.gf('django.db.models.fields.TextField')()),
            ('page', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('checksum', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('feeds', ['FeedEntry'])


    def backwards(self, orm):
        
        # Deleting model 'FeedEntry'
        db.delete_table('feeds_feedentry')


    models = {
        'feeds.feedentry': {
            'Meta': {'object_name': 'FeedEntry'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'checksum': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'page': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['feeds']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib import admin

from drumbeat.models import ModelBase


class FeedEntry(ModelBase):
    title = models.CharField(max_length=255)
    link = models.URLField()
    body = models.TextField()
    page = models.CharField(max_length=50)
    checksum = models.CharField(max_length=32, unique=True)
    created_on = models.DateTimeField()
    def __unicode__(self):
        return '%s - %s' % (
            self.title, 
            self.page
        )
admin.site.register(FeedEntry)

########NEW FILE########
__FILENAME__ = tasks
import time
import urllib2
import logging
import hashlib
import feedparser
import bleach

from django.conf import settings
from django.utils.encoding import smart_str

from celery.schedules import crontab
from celery.decorators import periodic_task

from feeds.models import FeedEntry

log = logging.getLogger(__name__)


def parse_entry(entry):
    """
    Given a feed entry, return a dictionary with 'title', 'content', 'link',
    'updated'.
    """
    title = getattr(entry, 'title', None)
    if not title:
        log.debug("Feed entry has no title element.")
        return None
    content = getattr(entry, 'content', None)
    # some feed entries have a summary but no content
    if not content:
        content = getattr(entry, 'summary', None)
    if  not content:
        log.debug("Feed entry has no content or summary element.")
        return None
    link = getattr(entry, 'link', None)
    if not link:
        log.debug("Feed entry has no link element.")
        return None
    updated = getattr(entry, 'updated_parsed', None)
    if not updated:
        log.debug("Feed entry has no updated element.")
        return None
    if type(content) == type([]):
        content = content[0]
    return {
        'title': title,
        'content': content,
        'link': link,
        'updated': updated,
    }


def get_feed_entries(feed_url):
    """Grab the 4 most recent feed entries from the splash page feed URL."""
    log.debug('Fetching feed from URL %s' % (feed_url,))
    if not feed_url:
        log.warn('No feed url defined. Cannot update splash page feed.')
        return []
    data = urllib2.urlopen(feed_url).read()
    feed = feedparser.parse(data)
    entries = feed.entries[0:4]
    return entries


def parse_feed(feed_url, page):
    ids = []
    entries = get_feed_entries(feed_url)
    for entry in entries: 
        parsed = parse_entry(entry)
        log.debug(parsed['title'])
        if not parsed:
            log.warn("Parsing feed failed. continuing")
            continue
        if isinstance(parsed['content'], feedparser.FeedParserDict):
            if 'value' in parsed['content'].keys():
                body = parsed['content']['value']
        else:
            body = parsed['content']
        if not body:
            log.warn("Parsing feed failed - no body found")
            continue
        cleaned_body = smart_str(bleach.clean(body, tags=(), strip=True))
        try:
            # [Bugzilla-670890]
            # Needed to allow for the same article but from different sources. This ensures a unique checksum per source
            checksum = hashlib.md5(cleaned_body + page).hexdigest() 
            exists = FeedEntry.objects.filter(checksum=checksum)
            if not exists:
                log.debug('Logging - %s' % parsed['title'])
                entry = FeedEntry(
                    title=parsed['title'].encode('utf-8'),
                    link=parsed['link'].encode('utf-8'),
                    body=cleaned_body,
                    page=page,
                    checksum=checksum,
                    created_on=time.strftime(
                        "%Y-%m-%d %H:%M:%S", parsed['updated']))
                entry.save()
                feed_id = entry.id
            else:
                # if it's already in the feed we still want to keep a reference to it's ID so we know to display it
                log.debug('Found a duplicate - entry')
                feed_id = exists[0].id
            ids.append(feed_id)
        except:
            log.warn("Encountered an error creating FeedEntry. Skipping.")
            continue
    log.debug(ids)
    return ids


@periodic_task(run_every=crontab(minute=0, hour=0))
def update_feeds():
    ids = []
    feeds = getattr(settings, 'FEED_URLS', None)
    if not feeds:
        log.debug("No feeds defined, aborting")
        return
    for page, feed_url in feeds.iteritems():
        parsed = parse_feed(feed_url, page)
        if parsed:
            ids.extend(parsed)
    if ids:
        FeedEntry.objects.exclude(id__in=ids).delete()

########NEW FILE########
__FILENAME__ = locales
# -*- coding: utf-8 -*-
# l10n support. Mostly taken from kitsune and zamboni.
#
# http://github.com/mozilla/kitsune
# http://github.com/mozilla/zamboni

from collections import namedtuple

import json
import os

Language = namedtuple(u'Language',
                      u'external internal english native dictionary')

file = os.path.join(os.path.dirname(__file__), 'languages.json')
locales = json.loads(open(file, 'r').read())

LOCALES = {}

for k in locales:
    LOCALES[k] = Language(locales[k]['external'], locales[k]['internal'],
                          locales[k]['English'], locales[k]['native'],
                          locales[k]['dictionary'])

INTERNAL_MAP = dict([(LOCALES[k].internal, k) for k in LOCALES])
LANGUAGES = dict([(i.lower(), LOCALES[i].native) for i in LOCALES])
LANGUAGE_URL_MAP = dict([(i.lower(), i) for i in LOCALES])

########NEW FILE########
__FILENAME__ = middleware
import urllib

from django.http import HttpResponsePermanentRedirect
from django.middleware.locale import LocaleMiddleware

from l10n import urlresolvers


class LocaleURLRewriter(LocaleMiddleware):

    def process_request(self, request):
        prefixer = urlresolvers.Prefixer(request)
        urlresolvers.set_url_prefix(prefixer)
        full_path = prefixer.fix(prefixer.shortened_path)

        if full_path != request.path:
            query_string = request.META.get('QUERY_STRING', '')
            full_path = urllib.quote(full_path.encode('utf-8'))

            if query_string:
                full_path = '%s?%s' % (full_path, query_string)

            response = HttpResponsePermanentRedirect(full_path)

            # Vary on Accept-Language if we changed the locale
            old_locale = prefixer.locale
            new_locale, _ = prefixer.split_path(full_path)
            if old_locale != new_locale:
                response['Vary'] = 'Accept-Language'

            return response

        request.path_info = '/' + prefixer.shortened_path
        request.locale = prefixer.locale
        request.META['HTTP_ACCEPT_LANGUAGE'] = request.locale

        super(LocaleURLRewriter, self).process_request(request)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = l10n_tags
from django import template
from django.utils.encoding import smart_str

from l10n.urlresolvers import reverse

register = template.Library()


class LocaleURLNode(template.Node):

    def __init__(self, node):
        self.node = node

    def render(self, context):
        args = [arg.resolve(context) for arg in self.node.args]
        kwargs = dict([(smart_str(k, 'ascii'), v.resolve(context))
                       for k, v in self.node.kwargs.items()])
        return reverse(self.node.view_name, args=args, kwargs=kwargs)


@register.tag
def locale_url(parser, token):
    node = template.defaulttags.url(parser, token)
    return LocaleURLNode(node)

########NEW FILE########
__FILENAME__ = tests
import re

from django.conf import settings
from django.test import Client

from users.models import UserProfile
from l10n import locales

import test_utils


class TestLocaleURLs(test_utils.TestCase):

    def setUp(self):
        self.client = Client()
        locales.LOCALES['de-DE'] = locales.Language(
            external=u'de-DE',
            internal=u'de',
            english=u'German',
            native=u'Deutsch',
            dictionary='de-DE',
        )

        locales.INTERNAL_MAP = dict(
            [(locales.LOCALES[k].internal, k) for k in locales.LOCALES])
        locales.LANGUAGES = dict(
            [(i.lower(), locales.LOCALES[i].native) for i in locales.LOCALES])
        locales.LANGUAGE_URL_MAP = dict(
            [(i.lower(), i) for i in locales.LOCALES])

    def test_default_rewrites(self):
        """Test that the client gets what they ask for if it's supported."""
        for supported in locales.LOCALES.keys():
            response = self.client.get('/', HTTP_ACCEPT_LANGUAGE=supported)
            self.assertRedirects(response, '/%s/' % (supported,),
                                 status_code=301)

    def test_specificity(self):
        """We support a more specific code than the general one sent."""
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='en')
        self.assertRedirects(response, '/en-US/', status_code=301)

    def test_close_match(self):
        """Client sends xx-YY, we support xx-ZZ. We give them xx-ZZ."""
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='en-CA')
        self.assertRedirects(response, '/en-US/', status_code=301)

    def test_general(self):
        """
        If the client sends a specific locale that is unsupported, we
        should check for a more general match (xx-YY -> xx).
        """
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='de-AT')
        self.assertRedirects(response, '/de-DE/', status_code=301)

    def test_unsupported_locale(self):
        """If locale is not supported, we should send them the default."""
        # if the default locale is not normalized, we'll get an additional 301
        default_locale = settings.LANGUAGE_CODE
        is_normalized = lambda l: re.match(r'[a-z]+-[A-Z]+', l) != None
        expected_target_code = is_normalized(default_locale) and 200 or 301
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='xx')
        self.assertRedirects(response,
                             '/%s/' % (default_locale,),
                             status_code=301,
                             target_status_code=expected_target_code)

    def test_normalized_case(self):
        """Accept-Language header is case insensitive."""
        response = self.client.get('/', HTTP_ACCEPT_LANGUAGE='en-us')
        self.assertRedirects(response, '/en-US/', status_code=301)

    def test_login_post_redirect(self):
        """Test that post requests are treated properly."""
        user = UserProfile.objects.create(
            username='testuser',
            email='test@mozilla.com',
        )
        user.set_password('testpass')
        user.save()
        user.create_django_user()
        response = self.client.get('/de-DE/login/')
        self.assertContains(response, 'csrfmiddlewaretoken')
        response = self.client.post('/de-DE/login/', {
            'username': user.username,
            'password': 'testpass',
        })
        self.assertRedirects(response, '/', status_code=302,
                             target_status_code=301)

########NEW FILE########
__FILENAME__ = urlresolvers
"""
Taken from kitsune.sumo.urlresolvers
"""
import threading

from django.conf import settings
from django.core.urlresolvers import reverse as django_reverse
from django.utils.translation.trans_real import parse_accept_lang_header

import l10n.locales

# Thread-local storage for URL prefixes. Access with (get|set)_url_prefix.
_locals = threading.local()


def set_url_prefix(prefix):
    """Set the ``prefix`` for the current thread."""
    _locals.prefix = prefix


def get_url_prefix():
    """Get the prefix for the current thread, or None."""
    return getattr(_locals, 'prefix', None)


def reverse(viewname, urlconf=None, args=None, kwargs=None,
            prefix=None, current_app=None):
    """Wraps Django's reverse to prepend the correct locale."""
    prefixer = get_url_prefix()

    if prefixer:
        prefix = prefix or '/'
    url = django_reverse(viewname, urlconf, args, kwargs, prefix, current_app)
    if prefixer:
        return prefixer.fix(url)
    else:
        return url


def find_supported(test):
    return [l10n.locales.LANGUAGE_URL_MAP[x] for
            x in l10n.locales.LANGUAGE_URL_MAP if
            x.split('-', 1)[0] == test.lower().split('-', 1)[0]]


class Prefixer(object):

    def __init__(self, request):
        self.request = request
        split = self.split_path(request.path_info)
        self.locale, self.shortened_path = split

    def split_path(self, path_):
        """
        Split the requested path into (locale, path).

        locale will be empty if it isn't found.
        """
        path = path_.lstrip('/')

        # Use partitition instead of split since it always returns 3 parts
        first, _, rest = path.partition('/')

        lang = first.lower()
        if lang in l10n.locales.LANGUAGE_URL_MAP:
            return l10n.locales.LANGUAGE_URL_MAP[lang], rest
        else:
            supported = find_supported(first)
            if len(supported):
                return supported[0], rest
            else:
                return '', path

    def get_language(self):
        """
        Return a locale code we support on the site using the
        user's Accept-Language header to determine which is best. This
        mostly follows the RFCs but read bug 439568 for details.
        """
        if 'lang' in self.request.GET:
            lang = self.request.GET['lang'].lower()
            if lang in l10n.locales.LANGUAGE_URL_MAP:
                return l10n.locales.LANGUAGE_URL_MAP[lang]

        if self.request.META.get('HTTP_ACCEPT_LANGUAGE'):
            ranked_languages = parse_accept_lang_header(
                self.request.META['HTTP_ACCEPT_LANGUAGE'])

            # Do we support or remap their locale?
            supported = [lang[0] for lang in ranked_languages if lang[0]
                        in l10n.locales.LANGUAGE_URL_MAP]

            # Do we support a less specific locale? (xx-YY -> xx)
            if not len(supported):
                for lang in ranked_languages:
                    supported = find_supported(lang[0])
                    if supported:
                        break

            if len(supported):
                return l10n.locales.LANGUAGE_URL_MAP[supported[0].lower()]

        return settings.LANGUAGE_CODE

    def fix(self, path):
        path = path.lstrip('/')
        url_parts = [self.request.META['SCRIPT_NAME']]

        if path.partition('/')[0] not in settings.SUPPORTED_NONLOCALES:
            locale = self.locale if self.locale else self.get_language()
            url_parts.append(locale)

        url_parts.append(path)

        return '/'.join(url_parts)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from links.models import Link

class LinksForm(forms.ModelForm):
    broadcast = forms.BooleanField(required=False)

    class Meta:
        model = Link
        fields = ('name', 'url', 'broadcast',)

    def save(self, commit=True):
        link = super(LinksForm, self).save(commit=False)
        link.broadcast = self.cleaned_data['broadcast']
        if commit:
            link.save()
        return link

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Link'
        db.create_table('links_link', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=1023)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'], null=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.UserProfile'], null=True)),
        ))
        db.send_create_signal('links', ['Link'])


    def backwards(self, orm):
        
        # Deleting model 'Link'
        db.delete_table('links_link')


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
        'links.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 25)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 25)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['links']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_link_subscription
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Link.subscription'
        db.add_column('links_link', 'subscription', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['subscriber.Subscription'], null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Link.subscription'
        db.delete_column('links_link', 'subscription_id')


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
        'links.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriber.Subscription']", 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 25)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 25)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['links']

########NEW FILE########
__FILENAME__ = models
import logging

from django.db import models
from django.db.models.signals import post_save, post_delete

from django_push.subscriber.models import Subscription
from django_push.subscriber.signals import updated

from links import tasks

log = logging.getLogger(__name__)


class Link(models.Model):
    """
    A link that can be added to a project or user. Links that have an Atom or
    RSS feed will be subscribed to using the declared hub or SuperFeedrs.
    """
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=1023)
    project = models.ForeignKey('projects.Project', null=True)
    user = models.ForeignKey('users.UserProfile', null=True)
    subscription = models.ForeignKey(Subscription, null=True)
    broadcast = False


def link_create_handler(sender, **kwargs):
    """Check for a feed and subscribe to it if it exists."""
    link = kwargs.get('instance', None)
    created = kwargs.get('created', False)

    if not link.broadcast:
        return

    if not created or not isinstance(link, Link):
        return

    tasks.SubscribeToFeed.apply_async(args=(link,))
post_save.connect(link_create_handler, sender=Link)


def link_delete_handler(sender, **kwargs):
    """If the link had an associated feed subscription, unsubscribe."""
    link = kwargs.get('instance', None)

    if not isinstance(link, Link):
        return

    if not link.subscription:
        return

    tasks.UnsubscribeFromFeed.apply_async(args=(link,))
post_delete.connect(link_delete_handler, sender=Link)


def listener(notification, **kwargs):
    """
    Create activity entries when we receive notifications of
    feed updates from a hub.
    """
    sender = kwargs.get('sender', None)
    if not sender:
        return
    try:
        tasks.HandleNotification.apply_async(args=(notification, sender))
    except:
        log.warn("Unprocessable notification: %s" % (notification,))
updated.connect(listener)

########NEW FILE########
__FILENAME__ = tasks
import urllib2

from django.conf import settings

from celery.task import Task
from django_push.subscriber.models import Subscription, SubscriptionError

from links import utils
from activity.models import RemoteObject, Activity


class SubscribeToFeed(Task):
    """
    Try to discover an Atom or RSS feed for the provided link and
    subscribe to it. Try to discover a hub declaration for the feed.
    If no hub is declared, fall back to using SuperFeedr.
    """

    max_retries = 3

    def run(self, link, **kwargs):
        log = self.get_logger(**kwargs)

        hub_url = None
        feed_url = None

        try:
            log.debug("Attempting feed discovery on %s" % (link.url,))
            html = urllib2.urlopen(link.url).read()
            feed_url = utils.parse_feed_url(html, link.url)
            log.debug("Found feed URL %s for %s" % (feed_url, link.url))
        except:
            log.warning("Error discoverying feed URL for %s. Retrying." % (
                link.url,))
            self.retry([link, ], kwargs)

        if not feed_url:
            return

        try:
            log.debug("Attempting hub discovery on %s" % (feed_url,))
            feed = urllib2.urlopen(feed_url).read()
            hub_url = utils.parse_hub_url(feed, feed_url)
            log.debug("Found hub %s for %s" % (hub_url, feed_url))
        except:
            log.warning("Error discoverying hub URL for %s. Retrying." % (
                feed_url,))
            self.retry([link, ], kwargs)

        try:
            hub = hub_url or settings.SUPERFEEDR_URL
            log.debug("Attempting subscription of topic %s with hub %s" % (
                feed_url, hub))
            subscription = Subscription.objects.subscribe(feed_url, hub=hub)
            log.info("Created subscription with callback url: %s" % (
                subscription.callback_url,))
        except SubscriptionError, e:
            log.warning("SubscriptionError. Retrying (%s)" % (link.url,))
            log.warning("Error: %s" % (str(e),))
            self.retry([link, ], kwargs)

        log.debug("Success. Subscribed to topic %s on hub %s" % (
            feed_url, hub))
        link.subscription = subscription
        link.save()


class UnsubscribeFromFeed(Task):
    """Simply send an unsubscribe request to the provided links hub."""

    def run(self, link, **kwargs):
        Subscription.objects.unsubscribe(link.subscription.topic,
                                         hub=link.subscription.hub)


class HandleNotification(Task):
    """
    When a notification of a new or updated entry is received, parse
    the entry and create an activity representation of it.
    """

    def get_activity_namespace_prefix(self, feed):
        """Discover the prefix used for the activity namespace."""
        namespaces = feed.namespaces
        activity_prefix = [prefix for prefix, ns in namespaces.iteritems()
                           if ns == 'http://activitystrea.ms/spec/1.0/']
        if activity_prefix:
            return activity_prefix[0]
        return None

    def get_namespaced_attr(self, entry, prefix, attr):
        """Feedparser prepends namespace prefixes to attribute names."""
        qname = '_'.join((prefix, attr))
        return getattr(entry, qname, None)

    def create_activity_entry(self, entry, sender, activity_prefix=None):
        """Create activity feed entries for the provided feed entry."""
        verb, object_type = None, None
        if activity_prefix:
            verb = self.get_namespaced_attr(
                entry, activity_prefix, 'verb')
            object_type = self.get_namespaced_attr(
                entry, activity_prefix, 'object-type')
        if not verb:
            verb = 'http://activitystrea.ms/schema/1.0/post'
        if not object_type:
            object_type = 'http://activitystrea.ms/schema/1.0/article'
        title = getattr(entry, 'title', None)
        uri = getattr(entry, 'link', None)
        if not (title and uri):
            self.log.warn("Received pubsub update with no title or uri")
            return
        for link in sender.link_set.all():
            self.log.info("Creating activity entry for link: %d" % (link.id,))
            remote_obj = RemoteObject(
                link=link, title=title, uri=uri, object_type=object_type)
            remote_obj.save()
            activity = Activity(
                actor=link.user, verb=verb, remote_object=remote_obj)
            if link.project:
                activity.target_project = link.project
            activity.save()

    def run(self, notification, sender, **kwargs):
        """Parse feed and create activity entries."""
        self.log = self.get_logger(**kwargs)
        prefix = self.get_activity_namespace_prefix(notification)
        for entry in notification.entries:
            self.log.debug("Received notification of entry: %s, %s" % (
                entry.title, entry.link))
            self.create_activity_entry(entry, sender, activity_prefix=prefix)

########NEW FILE########
__FILENAME__ = tests
import os
import urllib2
import feedparser
from StringIO import StringIO

from django_push.subscriber.models import Subscription

from links import utils, tasks
from links.models import Link

from test_utils import TestCase
from activity.models import Activity
from users.models import UserProfile


class MockFileObject(object):
    def read(self):
        return """
        <html>
        <head>
          <title>Test HTML</title>
          <link rel="alternate" type="application/rss+xml"
             href="http://example.com/rss">
        </head>
        <body>
           <h1>Test</h1>
        </body>
        </html>
        """

def mock_open_success(url):
    return MockFileObject()

def mock_open_failure(r):
    return urllib2.HTTPError('request', 204, 'no-op', {}, StringIO(''))

urllib2.urlopen = mock_open_failure
urllib2.Request = lambda x, y, z: 'request'


class TestLinkParsing(TestCase):

    def setUp(self):
        self.fixtures = {}
        root = os.path.dirname(os.path.abspath(__file__))
        fixture_dir = os.path.join(root, 'fixtures')
        for f in os.listdir(fixture_dir):
            self.fixtures[f] = file(os.path.join(fixture_dir, f)).read()

        self.user = UserProfile(username='testuser',
                                email='test@mozillafoundation.org')
        self.user.set_password('testpassword')
        self.user.save()
        self.user.create_django_user()

    def test_feed_parser(self):
        """Perform a straightforward test of the feed url parser."""
        html = """
        <html>
        <head>
          <title>Test HTML</title>
          <link rel="alternate" type="application/rss+xml"
             href="http://example.com/rss">
        </head>
        <body>
           <h1>Test</h1>
        </body>
        </html>
        """
        feed_url = utils.parse_feed_url(html)
        self.assertEqual('http://example.com/rss', feed_url)

    def test_feed_parser_multiple_alternates(self):
        """Test that given HTML with multiple feeds, the first is returned."""
        html = self.fixtures['selfhosted_wp_blog.html']
        feed_url = utils.parse_feed_url(html)
        self.assertEqual('http://blog.eval.ca/feed/', feed_url)

    def test_preference_of_atom(self):
        """Test that provided with RSS and Atom feeds, Atom comes out."""
        html = """
        <html>
          <head>
            <title>Test</title>
            <link rel="alternate" type="application/rss+xml"
              href="http://foo.com/rss" />
            <link rel="alternate" type="application/rss+xml"
              href="http://foo.com/comments/rss" />
            <link rel="alternate" type="application/atom+xml"
              href="http://foo.com/atom" />
            <link rel="alternate" type="application/atom+xml"
              href="http://foo.com/comments/atom" />
          </head>
        </html>
        """
        feed_url = utils.parse_feed_url(html)
        self.assertEqual('http://foo.com/atom', feed_url)

    def test_invalid_markup(self):
        """Test that parsing invalid markup works."""
        html = """<html><head><link rel="alternate" type="application/atom+xml"
        href="http://foo.com/atom"><body></html>"""
        feed_url = utils.parse_feed_url(html)
        self.assertEqual('http://foo.com/atom', feed_url)

    def test_hub_parser(self):
        """Test that we find a hub for a sample hosted WP rss feed."""
        rss = self.fixtures['rss_hub.rss']
        hub_url = utils.parse_hub_url(rss)
        self.assertEqual('http://commonspace.wordpress.com/?pushpress=hub',
                         hub_url)

    def test_hub_parser_no_hub(self):
        """Test that an rss feed with no hub declaration is returned as None"""
        rss = self.fixtures['rss_no_hub.rss']
        hub_url = utils.parse_hub_url(rss)
        self.assertEqual(None, hub_url)

    def test_hub_discovery(self):
        """Using a google buzz profile, find the atom feed and the hub url."""
        html = self.fixtures['buzz_profile.html']
        feed_url = utils.parse_feed_url(html)
        self.assertEqual(
            'https://www.googleapis.com/buzz/v1/activities/115398213828503499359/@public',
            feed_url)
        atom = self.fixtures['buzz_profile.atom']
        hub_url = utils.parse_hub_url(atom)
        self.assertEqual(
            'http://pubsubhubbub.appspot.com/',
            hub_url)

    def test_normalize_url(self):
        url = '/feed.rss'
        base_url = 'http://example.com'
        self.assertEqual('http://example.com/feed.rss',
                        utils.normalize_url(url, base_url))

    def test_normalize_url_two_slashes(self):
        url = '/feed.rss'
        base_url = 'http://example.com/'
        self.assertEqual('http://example.com/feed.rss',
                         utils.normalize_url(url, base_url))

    def test_normalize_url_trailing_slash_base(self):
        url = 'feed.rss'
        base_url = 'http://example.com/'
        self.assertEqual('http://example.com/feed.rss',
                         utils.normalize_url(url, base_url))

    def test_normalize_url_no_slashes(self):
        url = 'feed.rss'
        base_url = 'http://example.com'
        self.assertEqual('http://example.com/feed.rss',
                         utils.normalize_url(url, base_url))

    def test_normalize_url_good_url(self):
        url = 'http://example.com/atom'
        self.assertEqual(url, utils.normalize_url(url, 'http://example.com'))

    def test_notification(self):
        sub = Subscription.objects.create(
            hub='http://blah/', topic='http://blah')
        Link.objects.create(
            name='foo',
            url='http://blah/',
            subscription=sub,
            user=self.user)
        count = Activity.objects.count()
        test_feed_data = """<?xml version='1.0'?>
        <feed xmlns='http://www.w3.org/2005/Atom'
              xmlns:activity='http://activitystrea.ms/spec/1.0/'
              xml:lang='en-US'>
            <link type='text/html' rel='alternate' href='http://example.com'/>
            <link type='application/atom+xml' rel='self'
                href='http://example.com/feed/'/>
            <entry>
               <activity:verb>
                 http://activitystrea.ms/schema/1.0/follow
               </activity:verb>
               <activity:object-type>
                 http://activitystrea.ms/schema/1.0/person
               </activity:object-type>
               <link type='text/html' rel='alternate'
                   href='http://example.com/activity/'/>
               <title>Jane started following John</title>
            </entry>
        </feed>"""
        parsed = feedparser.parse(test_feed_data)
        handler = tasks.HandleNotification()
        handler.run(parsed, sub)
        self.assertEqual(Activity.objects.count(), count + 1)

########NEW FILE########
__FILENAME__ = utils
import urlparse

from xml import sax
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


from BeautifulSoup import BeautifulSoup

from django.conf import settings


def normalize_url(url, base_url):
    """Try to detect relative URLs and convert them into absolute URLs."""
    parts = urlparse.urlparse(url)
    if parts.scheme and parts.netloc:
        return url  # looks fine
    if not base_url:
        return url
    base_parts = urlparse.urlparse(base_url)
    server = '://'.join((base_parts.scheme, base_parts.netloc))
    if server[-1] != '/' and url[0] != '/':
        server = server + '/'
    if server[-1] == '/' and url[0] == '/':
        server = server[:-1]
    return server + url


class FeedHandler(sax.ContentHandler):
    """Parse RSS and Atom feeds and look for a PubSubHubbub hub."""
    href = None

    def startElementNS(self, name, qname, attrs):
        """Return href of link element with a rel attribute of 'hub'."""

        # stop processing if we encounter entries or items.
        if name == ('', 'item'):
            raise sax.SAXException('encountered item element')
        if name == ('http://www.w3.org/2005/Atom', 'entry'):
            raise sax.SAXException('encountered entry element')

        # only elements we're concerned with now are links
        if name != ('http://www.w3.org/2005/Atom', 'link'):
            return

        # drop namespace from attr names, build a dictionary of
        # local attribute name = value.
        fixed = {}
        for name, value in attrs.items():
            (namespace, local) = name
            fixed[local] = value

        # only concerned with links with 'hub' rel and an href attr.
        if not ('rel' in fixed and fixed['rel'] == 'hub'):
            return
        if not 'href' in fixed:
            return

        self.href = fixed['href']
        raise sax.SAXException('done')  # hacky way to signal that we're done.


def parse_feed_url(content, url=None):
    """
    Parse the provided html and return the first Atom or RSS feed we find.
    Note that a preference is given to Atom if the HTML contains links to
    both.
    """
    soup = BeautifulSoup(content)
    links = soup.findAll('link')

    # BeautifulSoup instances are not actually dictionaries, so
    # we can't use the more proper 'key in dict' syntax and
    # must instead use the deprecated 'has_key()' method.
    alternates = [link for link in links
                  if link.has_key('rel') and link['rel'] == 'alternate']
    get_by_type = lambda t, links: [l for l in links
                           if l.has_key('type') and l['type'] == t]
    get_hrefs = lambda links: [l['href'] for l in links if l.has_key('href')]
    atom = get_by_type('application/atom+xml', alternates)
    if atom:
        hrefs = get_hrefs(atom)
        if hrefs:
            return normalize_url(hrefs[0], url)
    rss = get_by_type('application/rss+xml', alternates)
    if rss:
        hrefs = get_hrefs(rss)
        if hrefs:
            return normalize_url(hrefs[0], url)
    return None


def parse_hub_url(content, base_url=None):
    """Parse the provided xml and find a hub link."""
    handler = FeedHandler()
    parser = sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(sax.handler.feature_namespaces, 1)
    inpsrc = sax.xmlreader.InputSource()
    inpsrc.setByteStream(StringIO(content))
    try:
        parser.parse(inpsrc)
    except sax.SAXException:
        pass
    if handler.href is None:
        return handler.href
    return normalize_url(handler.href, base_url)


def hub_credentials(hub_url):
    """Credentials callback for django_push.subscribers"""
    if hub_url == settings.SUPERFEEDR_URL:
        return (settings.SUPERFEEDR_USERNAME, settings.SUPERFEEDR_PASSWORD)
    return None

########NEW FILE########
__FILENAME__ = forms

########NEW FILE########
__FILENAME__ = models
from django.db import models

from drumbeat.models import ModelBase


class AccountPreferences(ModelBase):
    preferences = (
        'no_email_message_received',
        'no_email_new_follower',
        'no_email_new_project_follower',
        'no_email_mention',
    )
    key = models.CharField(max_length=50)
    value = models.CharField(max_length=100)
    user = models.ForeignKey('users.UserProfile')

########NEW FILE########
__FILENAME__ = tests
from django.core import mail
from test_utils import TestCase

from relationships.models import Relationship
from users.models import UserProfile
from preferences.models import AccountPreferences


class AccountPreferencesTests(TestCase):

    test_users = [
        dict(username='test_one', email='test_one@mozillafoundation.org'),
        dict(username='test_two', email='test_two@mozillafoundation.org'),
    ]

    def setUp(self):
        """Create data for testing."""
        for user in self.test_users:
            user = UserProfile(**user)
            user.set_password('testpass')
            user.save()
            user.create_django_user()
        (self.user_one, self.user_two) = UserProfile.objects.all()

    def test_new_follower_email_preference(self):
        """
        Test user is emailed when they get a new follower when that
        user wants to be emailed when they get a new follower.
        """
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_two,
        )
        relationship.save()
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to, [self.user_two.email, ])

    def test_no_new_follower_email_preference(self):
        """
        Test user is *not* emailed when they get a new follower when that user
        does *not* want to be emailed when they get a new follower.
        """
        AccountPreferences(user=self.user_two,
                           key='no_email_new_follower', value=1).save()
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_two,
        )
        relationship.save()
        self.assertEquals(len(mail.outbox), 0)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('',
  url(r'^settings/', 'preferences.views.settings',
      name='preferences_settings'),
  url(r'^delete/', 'preferences.views.delete',
      name='preferences_delete'),
)

########NEW FILE########
__FILENAME__ = views
import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from drumbeat import messages
from users.decorators import login_required
from preferences.models import AccountPreferences

log = logging.getLogger(__name__)


@login_required
def settings(request):
    profile = request.user.get_profile()
    if request.method == 'POST':
        for key in AccountPreferences.preferences:
            if key in request.POST and request.POST[key] == 'on':
                AccountPreferences.objects.filter(
                    user=profile, key=key).delete()
            else:
                AccountPreferences(
                    user=profile, key=key, value=1).save()
        messages.success(
            request,
            _("Thank you, your settings have been saved."))
        return HttpResponseRedirect(reverse('preferences_settings'))
    preferences = AccountPreferences.objects.filter(
        user=request.user.get_profile())
    prefs = {}
    for preference in preferences:
        log.debug("%s => %s" % (preference.key, preference.value))
        prefs[preference.key] = preference.value
    return render_to_response('preferences/settings_notifications.html', prefs,
                              context_instance=RequestContext(request))


@login_required
def delete(request):
    if request.method == 'POST':
        profile = request.user.get_profile()
        profile.user.delete()
        profile.delete()
        return HttpResponseRedirect(reverse('users_logout'))
    return render_to_response('preferences/settings_delete.html', {
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = decorators
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from projects.models import Project


def ownership_required(func):
    """
    Because I'm lazy, check here that the currently logged in user is
    the owner of the project specified by the ``slug`` kwarg. Return a
    403 response if they're not.
    """

    def decorator(*args, **kwargs):
        request = args[0]
        project = kwargs['slug']
        user = request.user.get_profile()
        project = get_object_or_404(Project, slug=project)
        if user != project.created_by:
            return HttpResponseForbidden()
        return func(*args, **kwargs)
    return decorator

########NEW FILE########
__FILENAME__ = forms
import logging

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from users import tasks
from projects.models import Project, ProjectMedia

log = logging.getLogger(__name__)


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ('name', 'short_description', 'long_description')


class ProjectDescriptionForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ('detailed_description',)
        widgets = {
            'detailed_description': forms.Textarea(attrs={'class': 'wmd'}),
        }


class ProjectImageForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ('image',)

    def clean_image(self):
        if self.cleaned_data['image'].size > settings.MAX_IMAGE_SIZE:
            max_size = settings.MAX_IMAGE_SIZE / 1024
            raise forms.ValidationError(
                _("Image exceeds max image size: %(max)dk" %
                  dict(max=max_size)))
        return self.cleaned_data['image']


class ProjectMediaForm(forms.ModelForm):

    allowed_content_types = (
        'video/ogg',
        'video/webm',
        'video/mp4',
        'application/ogg',
        'audio/ogg',
        'image/png',
        'image/jpg',
        'image/jpeg',
        'image/gif',
    )

    class Meta:
        model = ProjectMedia
        fields = ('project_file',)

    def clean_project_file(self):
        content_type = self.cleaned_data['project_file'].content_type
        if not content_type in ProjectMedia.accepted_mimetypes:
            log.warn("Attempt to upload unsupported file type: %s" % (
                content_type,))
            raise ValidationError(_('Unsupported file type.'))
        if self.cleaned_data['project_file'].size > settings.MAX_UPLOAD_SIZE:
            max_size = settings.MAX_UPLOAD_SIZE / 1024 / 1024
            raise ValidationError(
                _("File exceeds max file size: %(max)dMB" % {
                    'max': max_size,
                 }),
            )
        return self.cleaned_data['project_file']


class ProjectContactUsersForm(forms.Form):
    """
    A modified version of ``messages.forms.ComposeForm`` that enables
    project admins to send a message to all of the users who follow
    their project.
    """
    project = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(),
    )
    subject = forms.CharField(label=_(u'Subject'))
    body = forms.CharField(
        label=_(u'Body'),
        widget=forms.Textarea(attrs={'rows': '12', 'cols': '55'}),
    )

    def save(self, sender, parent_msg=None):
        project = self.cleaned_data['project']
        try:
            project = Project.objects.get(id=int(project))
        except Project.DoesNotExist:
            raise forms.ValidationError(
                _(u'Hmm, that does not look like a valid project'))
        recipients = project.followers()
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        messages = [(sender, r.user, subject, body, parent_msg)
                    for r in recipients]
        tasks.SendUsersEmail.apply_async(args=(self, messages))
        return messages

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Project'
        db.create_table('projects_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50, db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('call_to_action', self.gf('django.db.models.fields.TextField')()),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects', to=orm['auth.User'])),
            ('featured', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('template', self.gf('django.db.models.fields.TextField')()),
            ('css', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('projects', ['Project'])

        # Adding model 'Link'
        db.create_table('projects_link', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'])),
        ))
        db.send_create_signal('projects', ['Link'])


    def backwards(self, orm):
        
        # Deleting model 'Project'
        db.delete_table('projects_project')

        # Deleting model 'Link'
        db.delete_table('projects_link')


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
        'projects.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_link_feed_url__add_unique_link_project_url
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Link.feed_url'
        db.add_column('projects_link', 'feed_url', self.gf('django.db.models.fields.URLField')(default='', max_length=200), keep_default=False)

        # Adding unique constraint on 'Link', fields ['project', 'url']
        db.create_unique('projects_link', ['project_id', 'url'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Link', fields ['project', 'url']
        db.delete_unique('projects_link', ['project_id', 'url'])

        # Deleting field 'Link.feed_url'
        db.delete_column('projects_link', 'feed_url')


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
        'projects.link': {
            'Meta': {'unique_together': "(('project', 'url'),)", 'object_name': 'Link'},
            'feed_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0003_auto__add_field_link_created_on__add_field_project_created_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Link.created_on'
        db.add_column('projects_link', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 11, 29), auto_now_add=True, blank=True), keep_default=False)

        # Adding field 'Project.created_on'
        db.add_column('projects_project', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 11, 29), auto_now_add=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Link.created_on'
        db.delete_column('projects_link', 'created_on')

        # Deleting field 'Project.created_on'
        db.delete_column('projects_project', 'created_on')


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
        'projects.link': {
            'Meta': {'unique_together': "(('project', 'url'),)", 'object_name': 'Link'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 11, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 11, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_project_created_by
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Project.created_by'
        db.alter_column('projects_project', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.UserProfile']))


    def backwards(self, orm):
        
        # Changing field 'Project.created_by'
        db.alter_column('projects_project', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))


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
        'projects.link': {
            'Meta': {'unique_together': "(('project', 'url'),)", 'object_name': 'Link'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'feed_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0005_auto__del_link__del_unique_link_project_url__del_field_project_descrip
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Link', fields ['project', 'url']
        #db.delete_unique('projects_link', ['project_id', 'url'])

        # Deleting model 'Link'
        db.delete_table('projects_link')

        # Deleting field 'Project.description'
        db.delete_column('projects_project', 'description')

        # Deleting field 'Project.call_to_action'
        db.delete_column('projects_project', 'call_to_action')

        # Deleting field 'Project.template'
        db.delete_column('projects_project', 'template')

        # Deleting field 'Project.css'
        db.delete_column('projects_project', 'css')

        # Adding field 'Project.short_description'
        db.add_column('projects_project', 'short_description', self.gf('django.db.models.fields.CharField')(default='default', max_length=100), keep_default=False)

        # Adding field 'Project.long_description'
        db.add_column('projects_project', 'long_description', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)

        # Adding field 'Project.detailed_description'
        db.add_column('projects_project', 'detailed_description', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)


    def backwards(self, orm):
        
        # Adding model 'Link'
        db.create_table('projects_link', (
            ('feed_url', self.gf('django.db.models.fields.URLField')(default='', max_length=200)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'])),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 12, 18), auto_now_add=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('projects', ['Link'])

        # Adding unique constraint on 'Link', fields ['project', 'url']
        db.create_unique('projects_link', ['project_id', 'url'])

        # Adding field 'Project.description'
        db.add_column('projects_project', 'description', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)

        # Adding field 'Project.call_to_action'
        db.add_column('projects_project', 'call_to_action', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)

        # Adding field 'Project.template'
        db.add_column('projects_project', 'template', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)

        # Adding field 'Project.css'
        db.add_column('projects_project', 'css', self.gf('django.db.models.fields.TextField')(default='default'), keep_default=False)

        # Deleting field 'Project.short_description'
        db.delete_column('projects_project', 'short_description')

        # Deleting field 'Project.long_description'
        db.delete_column('projects_project', 'long_description')

        # Deleting field 'Project.detailed_description'
        db.delete_column('projects_project', 'detailed_description')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0006_auto__add_projectmedia
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ProjectMedia'
        db.create_table('projects_projectmedia', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project_file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'])),
        ))
        db.send_create_signal('projects', ['ProjectMedia'])


    def backwards(self, orm):
        
        # Deleting model 'ProjectMedia'
        db.delete_table('projects_projectmedia')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_projectmedia_mime_type
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ProjectMedia.mime_type'
        db.add_column('projects_projectmedia', 'mime_type', self.gf('django.db.models.fields.CharField')(max_length=80, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ProjectMedia.mime_type'
        db.delete_column('projects_projectmedia', 'mime_type')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 30)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_project_image
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Project.image'
        db.add_column('projects_project', 'image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Project.image'
        db.delete_column('projects_project', 'image')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_project_detailed_description_html
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Project.detailed_description_html'
        db.add_column('projects_project', 'detailed_description_html', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Project.detailed_description_html'
        db.delete_column('projects_project', 'detailed_description_html')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 8)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_projectmedia_thumbnail
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ProjectMedia.thumbnail'
        db.add_column('projects_projectmedia', 'thumbnail', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ProjectMedia.thumbnail'
        db.delete_column('projects_projectmedia', 'thumbnail')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 14)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 14)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = 0011_auto__chg_field_project_short_description
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Project.short_description'
        db.alter_column('projects_project', 'short_description', self.gf('django.db.models.fields.CharField')(max_length=125))


    def backwards(self, orm):
        
        # Changing field 'Project.short_description'
        db.alter_column('projects_project', 'short_description', self.gf('django.db.models.fields.CharField')(max_length=100))


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'projects.projectmedia': {
            'Meta': {'object_name': 'ProjectMedia'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']"}),
            'project_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'thumbnail': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 23)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['projects']

########NEW FILE########
__FILENAME__ = models
import os
import logging
import datetime
import bleach

from markdown import markdown

from django.core.cache import cache
from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django.db.models.signals import pre_save, post_save, post_delete
from django.template.defaultfilters import slugify

from drumbeat import storage
from drumbeat.utils import get_partition_id, safe_filename
from drumbeat.models import ModelBase
from relationships.models import Relationship

from projects.utils import strip_remote_images
from projects.tasks import ThumbnailGenerator

import caching.base

TAGS = ('h1', 'h2', 'a', 'b', 'em', 'i', 'strong',
        'ol', 'ul', 'li', 'hr', 'blockquote', 'p',
        'span', 'pre', 'code', 'img')

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt'],
}

log = logging.getLogger(__name__)


def determine_image_upload_path(instance, filename):
    return "images/projects/%(partition)d/%(filename)s" % {
        'partition': get_partition_id(instance.pk),
        'filename': safe_filename(filename),
    }


def determine_media_upload_path(instance, filename):
    if instance.is_video():
        fmt = "videos/projects/%(partition)d/%(filename)s"
    else:
        fmt = "images/projects/%(partition)d/%(filename)s"
    return fmt % {
        'partition': get_partition_id(instance.project.pk),
        'filename': safe_filename(filename),
    }


class ProjectManager(caching.base.CachingManager):

    def get_popular(self, limit=0):
        popular = cache.get('projects_popular')
        if not popular:
            rels = Relationship.objects.values('target_project').annotate(
                Count('id')).exclude(target_project__isnull=True).filter(
                target_project__featured=False).order_by('-id__count')[:limit]
            popular = [r['target_project'] for r in rels]
            cache.set('projects_popular', popular, 3000)
        return Project.objects.filter(id__in=popular)


class Project(ModelBase):
    """Placeholder model for projects."""
    object_type = 'http://drumbeat.org/activity/schema/1.0/project'
    generalized_object_type = 'http://activitystrea.ms/schema/1.0/group'

    name = models.CharField(max_length=100, unique=True)
    short_description = models.CharField(max_length=125)
    long_description = models.TextField()

    detailed_description = models.TextField()
    detailed_description_html = models.TextField(null=True, blank=True)

    image = models.ImageField(upload_to=determine_image_upload_path, null=True,
                              storage=storage.ImageStorage(), blank=True)

    slug = models.SlugField(unique=True)
    created_by = models.ForeignKey('users.UserProfile',
                                   related_name='projects')
    featured = models.BooleanField()
    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.date.today())

    objects = ProjectManager()

    def followers(self):
        """Return a list of users following this project."""
        relationships = Relationship.objects.select_related(
            'source', 'created_by').filter(target_project=self)
        return [rel.source for rel in relationships]

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('projects_show', (), {
            'slug': self.slug,
        })

    def save(self):
        """Make sure each project has a unique slug."""
        count = 1
        if not self.slug:
            slug = slugify(self.name)
            self.slug = slug
            while True:
                existing = Project.objects.filter(slug=self.slug)
                if len(existing) == 0:
                    break
                self.slug = slug + str(count)
                count += 1
        super(Project, self).save()
admin.site.register(Project)


class ProjectMedia(ModelBase):
    video_mimetypes = (
        'video/ogg',
        'video/webm',
        'video/mp4',
        'application/ogg',
        'audio/ogg',
    )
    image_mimetypes = (
        'image/png',
        'image/jpg',
        'image/jpeg',
        'image/gif',
    )
    accepted_mimetypes = video_mimetypes + image_mimetypes
    project_file = models.FileField(upload_to=determine_media_upload_path)
    project = models.ForeignKey(Project)
    mime_type = models.CharField(max_length=80, null=True)
    thumbnail = models.ImageField(upload_to=determine_image_upload_path,
                                  null=True, blank=True,
                                  storage=storage.ImageStorage())

    def thumbnail_or_default(self):
        """Return project media's thumbnail or a default."""
        return self.thumbnail or 'images/file-default.png'

    def is_video(self):
        return self.mime_type in self.video_mimetypes


###########
# Signals #
###########


def project_markdown_handler(sender, **kwargs):
    project = kwargs.get('instance', None)
    if not isinstance(project, Project):
        return
    log.debug("Creating html project description")
    if project.detailed_description:
        project.detailed_description_html = bleach.clean(
            markdown(project.detailed_description),
            tags=TAGS, attributes=ALLOWED_ATTRIBUTES)
        project.detailed_description_html = strip_remote_images(
            project.detailed_description_html, project.pk)

pre_save.connect(project_markdown_handler, sender=Project)


def project_creation_handler(sender, **kwargs):
    project = kwargs.get('instance', None)
    created = kwargs.get('created', False)

    if not created or not isinstance(project, Project):
        log.debug("Nothing to do, returning")
        return

    log.debug("Creating relationship between project creator and project")
    Relationship(source=project.created_by,
                 target_project=project).save()

    try:
        from activity.models import Activity
        act = Activity(actor=project.created_by,
                       verb='http://activitystrea.ms/schema/1.0/post',
                       project=project)
        act.save()
    except ImportError:
        return
post_save.connect(project_creation_handler, sender=Project)


def projectmedia_thumbnail_generator(sender, **kwargs):
    media = kwargs.get('instance', None)
    created = kwargs.get('created', False)

    if not created or not isinstance(media, ProjectMedia):
        return

    ThumbnailGenerator.apply_async(args=(media,))
post_save.connect(projectmedia_thumbnail_generator, sender=ProjectMedia)


def projectmedia_scrubber(sender, **kwargs):
    media = kwargs.get('instance', None)
    if not isinstance(media, ProjectMedia):
        return
    media_root = getattr(settings, 'MEDIA_ROOT', None)
    if not media_root:
        return
    path = lambda f: os.path.join(media_root, f)
    files = []
    if media.project_file:
        files.append(path(media.project_file.name))
    if media.thumbnail:
        files.append(path(media.thumbnail.name))
    for f in files:
        if os.path.exists(f):
            os.unlink(f)
post_delete.connect(projectmedia_scrubber, sender=ProjectMedia)

########NEW FILE########
__FILENAME__ = tasks
import os
import glob
import logging
import random

import Image

from django.conf import settings

from celery.task import Task

from drumbeat.utils import get_partition_id

log = logging.getLogger(__name__)


class ThumbnailGenerator(Task):

    def determine_path(self, project, filename):
        return "images/projects/%(partition)d/%(filename)s" % {
            'partition': get_partition_id(project.pk),
            'filename': filename,
        }

    def create_frames(self, media):
        """
        Using ffmpeg, extract one image per frame for the first n frames
        of a video file, where n is specified by the ``FFMPEG_VFRAMES``
        configuration variable.
        """
        working_dir = getattr(settings, 'FFMPEG_WD', '/tmp')
        abs_path = os.path.join(settings.MEDIA_ROOT, media.project_file.name)
        framemask = self.frame_prefix + ".%d.jpg"
        cmd = '%s -y -an -vframes %d -r 1 -i %s %s -v 1 > /dev/null 2>&1' % (
            self.ffmpeg, self.vframes, abs_path, framemask)
        os.chdir(working_dir)
        return_value = os.system(cmd)
        log.debug("Running command: %s" % (cmd,))
        if return_value != 0:
            log.warn("ffmpeg returned non-zero: %d" % (return_value,))
            return False
        return True

    def create_video_thumbnail(self, media):
        """
        Select a random frame from the video to use as the video thumbnail.
        """
        image = "%s.%d.jpg" % (self.frame_prefix,
                               random.choice(range(1, self.vframes + 1)),)
        if not os.path.exists(image):
            log.warn("File %s does not exist!" % (image,))
            return
        thumbnail, ext = os.path.splitext(os.path.basename(image))
        thumbnail_filename = self.determine_path(
            media.project, "%s_thumbnail.png" % (thumbnail,))
        media.thumbnail = thumbnail_filename
        media.save()
        abs_path = os.path.join(settings.MEDIA_ROOT, thumbnail_filename)
        im = Image.open(image)
        im.thumbnail((128, 128), Image.ANTIALIAS)
        im.save(abs_path, 'PNG')
        return True

    def create_image_thumbnail(self, media):
        """Create a thumbnail for an image using PIL."""
        image = os.path.join(settings.MEDIA_ROOT, media.project_file.name)
        thumbnail_filename = self.determine_path(
            media.project, "%s_thumbnail.%s" % (os.path.splitext(
                os.path.basename(media.project_file.name))))
        thumbnail_path = os.path.join(settings.MEDIA_ROOT, thumbnail_filename)
        im = Image.open(image)
        im.thumbnail((128, 128), Image.ANTIALIAS)
        im.save(thumbnail_path, im.format)
        media.thumbnail = thumbnail_filename
        media.save()
        return True

    def run(self, media):

        self.ffmpeg = getattr(settings, 'FFMPEG_PATH', None)
        self.vframes = getattr(settings, 'FFMPEG_VFRAMES', 10)

        if not media.is_video():
            return self.create_image_thumbnail(media)

        if not self.ffmpeg:
            log.warn("No ffmpeg path set. Nothing to do.")
            return

        self.frame_prefix = "frame%d_%d" % (media.project.id, media.id)

        if not self.create_frames(media):
            log.warn("Error creating frames.")
            return

        if not self.create_video_thumbnail(media):
            log.warn("Error creating thumbnail")
            return

        # remove frame image files.
        files = glob.glob(self.frame_prefix + '*')
        for f in files:
            os.unlink(f)

########NEW FILE########
__FILENAME__ = tests
from django.test import Client

from users.models import UserProfile
from activity.models import Activity
from projects.models import Project

from test_utils import TestCase


class ProjectTests(TestCase):

    test_username = 'testuser'
    test_email = 'test@mozillafoundation.org'
    test_password = 'testpass'

    def setUp(self):
        self.client = Client()
        self.locale = 'en-US'
        self.client = Client()
        self.user = UserProfile(
            username=self.test_username,
            email=self.test_email,
        )
        self.user.set_password(self.test_password)
        self.user.save()
        self.user.create_django_user()

    def test_unique_slugs(self):
        """Test that each project will get a unique slug"""
        project = Project(
            name='My Cool Project',
            short_description='This project is awesome',
            long_description='No really, its good',
            created_by=self.user,
        )
        project.save()
        self.assertEqual('my-cool-project', project.slug)
        project2 = Project(
            name='My Cool  Project',
            short_description='This project is awesome',
            long_description='This is all very familiar',
            created_by=self.user,
        )
        project2.save()
        self.assertEqual('my-cool-project1', project2.slug)

    def test_activity_firing(self):
        """Test that when a project is created, an activity is created."""
        activities = Activity.objects.all()
        self.assertEqual(0, len(activities))
        project = Project(
            name='My Cool Project',
            short_description='This project is awesome',
            long_description='Yawn',
            created_by=self.user,
        )
        project.save()
        # expect 2 activities, a create and a follow
        activities = Activity.objects.all()
        self.assertEqual(2, len(activities))
        for activity in activities:
            self.assertEqual(self.user, activity.actor.user.get_profile())
            self.assertEqual(project, activity.project)
            self.assertTrue(activity.verb in (
                'http://activitystrea.ms/schema/1.0/post',
                'http://activitystrea.ms/schema/1.0/follow',
           ))

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
  url(r'^$', 'projects.views.list',
      name='projects_gallery'),
  url(r'^all/$', 'projects.views.list_all',
      name='projects_directory'),
  url(r'^all/(?P<page>\d+)/$', 'projects.views.list_all',
      name='projects_directory'),
  url(r'^create/$', 'projects.views.create',
      name='projects_create'),
  url(r'^(?P<slug>[\w-]+)/$', 'projects.views.show',
      name='projects_show'),
  url(r'^(?P<slug>[\w-]+)/description/$', 'projects.views.show_detailed',
      name='projects_show_detailed'),
  url(r'^(?P<slug>[\w-]+)/contactfollowers/$',
      'projects.views.contact_followers',
      name='projects_contact_followers'),

  # Project Edit URLs
  url(r'^(?P<slug>[\w-]+)/edit/$', 'projects.views.edit',
      name='projects_edit'),
  url(r'^(?P<slug>[\w-]+)/edit/description/$',
      'projects.views.edit_description',
      name='projects_edit_description'),
  url(r'^(?P<slug>[\w-]+)/edit/image/$',
      'projects.views.edit_image',
      name='projects_edit_image'),
  url(r'^(?P<slug>[\w-]+)/edit/ajax_image/$',
      'projects.views.edit_image_async',
      name='projects_edit_image_async'),
  url(r'^(?P<slug>[\w-]+)/edit/links/$',
      'projects.views.edit_links',
      name='projects_edit_links'),
  url(r'^(?P<slug>[\w-]+)/edit/links/(?P<link>\d+)/delete/$',
      'projects.views.edit_links_delete',
      name='projects_edit_links_delete'),
)

########NEW FILE########
__FILENAME__ = utils
import os
import tempfile
import urllib2
import Image
import logging

from lxml import html

from django.conf import settings

from drumbeat.utils import get_partition_id, safe_filename

log = logging.getLogger(__name__)


def determine_image_upload_path(instance, filename):
    return "images/projects/%(partition)d/%(filename)s" % {
        'partition': get_partition_id(instance.pk),
        'filename': safe_filename(filename),
    }


class Mock(object):

    def __init__(self, pk):
        self.pk = pk

format_extensions = {
    'PNG': 'png',
    'GIF': 'gif',
    'JPEG': 'jpg',
    'JPG': 'jpg',
}

mime_types_extensions = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
}

image_mime_types = mime_types_extensions.keys()


def copy_image(image_url):
    """
    Download an image into a temp file, transcode the image and save it in
    the project image directory.
    """
    try:
        image_fp = urllib2.urlopen(image_url, timeout=5)
    except urllib2.URLError:
        log.warn("Error opening %s. Returning." % (image_url,))
        return None

    if not image_fp:
        log.warn("Error opening %s. Returning." % (image_url,))
        return None
    headers = image_fp.info()

    max_image_size = getattr(settings, 'MAX_IMAGE_SIZE', None)
    if not max_image_size:
        log.warn("No MAX_IMAGE_SIZE set")
        return None

    # check that file is not too large and is an image.
    if 'Content-Length' not in headers:
        log.warn("No content-length in headers. Returning")
        return None
    if int(headers['Content-Length']) > max_image_size:
        log.warn("Content-length header exceeds max allowable size. Returning")
        return None
    if headers['Content-Type'] not in image_mime_types:
        log.warn("Content-type header not an allowable mime type. Returning")
        return None

    tmpfile, tmpfile_name = tempfile.mkstemp()
    tmpfile_fp = os.fdopen(tmpfile, 'w+b')

    downloaded = 0
    chunk_size = 1024
    while True:
        chunk = image_fp.read(chunk_size)
        if not chunk:
            break
        downloaded += chunk_size
        if downloaded > max_image_size:
            tmpfile_fp.close()
            image_fp.close()
            os.unlink(tmpfile_fp)
            return None
        tmpfile_fp.write(chunk)

    tmpfile_fp.close()
    image_fp.close()

    return tmpfile_name


def strip_remote_images(content, pk):
    """
    Find all img tags in content. Download the image referred to in the src
    attribute, run it through PIL to strip out any comments, and replace
    the attribute value with a local url.
    """
    tree = html.fromstring(content)
    img_urls = [img.get('src', None) for img in tree.xpath('//img')]

    media_root = getattr(settings, 'MEDIA_ROOT', None)
    media_url = getattr(settings, 'MEDIA_URL', None)

    if not media_root or not media_url:
        return None

    new_urls = []
    for img_url in img_urls:
        tmpfile = copy_image(img_url)
        if tmpfile is None:
            new_urls.append("")
            continue
        try:
            image_basename = img_url.split('/')[-1]
            image_path = determine_image_upload_path(Mock(pk), image_basename)
            destination = os.path.join(media_root, image_path)

            image = Image.open(tmpfile)
            basename, ext = os.path.splitext(destination)
            if (ext[1:] not in mime_types_extensions.values()):
                destination = "%s.%s" % (
                    basename, format_extensions[image.format])
            image.save(destination, image.format)
            new_urls.append(os.path.join(media_url, image_path))
        except Exception, e:
            log.warn("Error stripping out remote image: %s" % (e,))
            new_urls.append("")
        finally:
            os.unlink(tmpfile)

    for i in range(len(img_urls)):
        # markdown replaces & with &amp; even if it's part of a querystring
        old = img_urls[i].replace('&', '&amp;')
        new = new_urls[i]
        log.debug("replacing %s with %s" % (old, new))
        content = content.replace(old, new)

    return content

########NEW FILE########
__FILENAME__ = views
import logging

from django import http
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponsePermanentRedirect
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_http_methods

from commonware.decorators import xframe_sameorigin

from projects import forms as project_forms
from projects.decorators import ownership_required
from projects.models import Project, ProjectMedia

from relationships.models import Relationship
from activity.models import Activity
from links.models import Link
from links import forms as link_forms
from statuses.models import Status
from drumbeat import messages
from users.models import UserProfile
from users.decorators import login_required
from challenges.models import Challenge

log = logging.getLogger(__name__)

drumbeat_redirects = {
    'universal-subtitles': 'https://www.universalsubtitles.org',
    'hackasaurus': 'http://www.hackasaurus.org',
    'popcornjs': 'http://www.mozillapopcorn.org',
    'webmademovies': 'http://www.mozillapopcorn.org',
    'school-of-webcraft': 'http://www.p2pu.org/webcraft/',
    'mojo': 'http://www.mozillaopennews.org',
    'open-web-badges': 'http://www.openbadges.org',
    'open-attribute': 'http://www.openattribute.com',
    'privacy-icons': 'http://wiki.mozilla.org/Privacy_Icons',
    'open-web-publishing': 'http://www.sourcefabric.org/en/booktype/',
    'floss-manuals-drumbeat-book-shelf': 'http://www.flossmanuals.net/',
}

def move_on(request, slug):
    projects = drumbeat_redirects.keys()
    if slug in projects:
        return HttpResponsePermanentRedirect(drumbeat_redirects[slug])
    else:
        return HttpResponseRedirect('/')

def show(request, slug):
    project = get_object_or_404(Project, slug=slug)
    is_following = False
    if request.user.is_authenticated():
        try:
            profile = request.user.get_profile()
            is_following = profile.is_following(project)
        except UserProfile.DoesNotExist:
            is_following = False
    activities = Activity.objects.filter(
        Q(project=project) | Q(target_project=project),
    ).exclude(
        verb='http://activitystrea.ms/schema/1.0/follow'
    ).order_by('-created_on')[0:10]
    nstatuses = Status.objects.filter(project=project).count()
    links = project.link_set.all()
    files = project.projectmedia_set.all()
    followers_count = Relationship.objects.filter(
        target_project=project).count()
    challenges = Challenge.objects.filter(project=project)

    context = {
        'project': project,
        'following': is_following,
        'followers_count': followers_count,
        'activities': activities,
        'update_count': nstatuses,
        'links': links,
        'files': files,
        'challenges': challenges,
    }
    return render_to_response('projects/project.html', context,
                              context_instance=RequestContext(request))


def show_detailed(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render_to_response('projects/project_full_description.html', {
        'project': project,
    }, context_instance=RequestContext(request))


@login_required
@ownership_required
def edit(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        form = project_forms.ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, _('Project updated!'))
            return http.HttpResponseRedirect(
                reverse('projects_edit', kwargs=dict(slug=project.slug)))
    else:
        form = project_forms.ProjectForm(instance=project)

    return render_to_response('projects/project_edit_summary.html', {
        'form': form,
        'project': project,
    }, context_instance=RequestContext(request))


@login_required
@ownership_required
def edit_description(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        form = project_forms.ProjectDescriptionForm(
            request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, _('Project description updated!'))
            return http.HttpResponseRedirect(
                reverse('projects_edit_description', kwargs={
                'slug': project.slug,
            }))
        else:
            messages.error(request,
                           _('There was a problem saving your description.'))
    else:
        form = project_forms.ProjectDescriptionForm(instance=project)
    return render_to_response('projects/project_edit_description.html', {
        'form': form,
        'project': project,
    }, context_instance=RequestContext(request))


@login_required
@xframe_sameorigin
@ownership_required
@require_http_methods(['POST'])
def edit_image_async(request, slug):
    project = get_object_or_404(Project, slug=slug)
    form = project_forms.ProjectImageForm(request.POST, request.FILES,
                                          instance=project)
    if form.is_valid():
        instance = form.save()
        return http.HttpResponse(simplejson.dumps({
            'filename': instance.image.name,
        }))
    return http.HttpResponse(simplejson.dumps({
        'error': 'There was an error uploading your image.',
    }))


@login_required
@ownership_required
def edit_image(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        form = project_forms.ProjectImageForm(request.POST, request.FILES,
                                              instance=project)
        if form.is_valid():
            messages.success(request, _('Project image updated'))
            form.save()
            return http.HttpResponseRedirect(reverse('projects_show', kwargs={
                'slug': project.slug,
            }))
        else:
            messages.error(request,
                           _('There was an error uploading your image'))
    else:
        form = project_forms.ProjectImageForm(instance=project)
    return render_to_response('projects/project_edit_image.html', {
        'project': project,
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
@ownership_required
def edit_media(request, slug):
    project = get_object_or_404(Project, slug=slug)
    files = project.projectmedia_set.all()
    if request.method == 'POST':
        if files.count() > settings.MAX_PROJECT_FILES:
            messages.error(request, _('You have already used up your allotted '
                                      'number of file uploads. Please delete '
                                      'some files and try again.'))
            return http.HttpResponseRedirect(
                reverse('projects_edit_media', kwargs=dict(slug=project.slug)))
        form = project_forms.ProjectMediaForm(request.POST, request.FILES)
        if form.is_valid():
            messages.success(request, _('File uploaded'))
            media = form.save(commit=False)
            media.project = project
            media.mime_type = form.cleaned_data['project_file'].content_type
            media.save()
            return http.HttpResponseRedirect(
                reverse('projects_edit_media', kwargs=dict(slug=project.slug)))
        else:
            messages.error(request, _('There was an error uploading '
                                      'your file.'))
    else:
        form = project_forms.ProjectMediaForm()
    return render_to_response('projects/project_edit_media.html', {
        'files': files,
        'form': form,
        'project': project,
    }, context_instance=RequestContext(request))


@login_required
@ownership_required
@require_http_methods(['POST'])
def delete_media(request, slug):
    project = get_object_or_404(Project, slug=slug)
    file_id = int(request.POST['file_id'])
    file_obj = ProjectMedia.objects.get(
        project=project, pk=file_id)
    file_obj.delete()
    messages.success(request, _("The file has been deleted."))
    return http.HttpResponseRedirect(reverse('projects_edit_media', kwargs={
        'slug': project.slug,
    }))


@login_required
@ownership_required
def edit_links(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        form = link_forms.LinksForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.project = project
            link.user = project.created_by
            link.save()
            messages.success(request, _('Project link added.'))
            return http.HttpResponseRedirect(
                reverse('projects_edit_links', kwargs=dict(slug=project.slug)))
        else:
            messages.error(request, _('There was an error adding your link.'))
    else:
        form = link_forms.LinksForm()
    links = Link.objects.select_related('subscription').filter(project=project)
    return render_to_response('projects/project_edit_links.html', {
        'project': project,
        'form': form,
        'links': links,
    }, context_instance=RequestContext(request))


@login_required
@ownership_required
def edit_links_delete(request, slug, link):
    if request.method == 'POST':
        project = get_object_or_404(Project, slug=slug)
        link = get_object_or_404(Link, pk=link)
        if link.project != project:
            return http.HttpResponseForbidden()
        link.delete()
        messages.success(request, _('The link was deleted'))
    return http.HttpResponseRedirect(
        reverse('projects_edit_links', kwargs=dict(slug=slug)))


def list_all(request, page=1):
    projects = Project.objects.all()
    paginator = Paginator(projects, 16)
    try:
        current_page = paginator.page(page)
    except EmptyPage:
        raise http.Http404
    projects = current_page.object_list
    for project in projects:
        project.followers_count = Relationship.objects.filter(
            target_project=project).count()
    return render_to_response('projects/directory.html', {
        'paginator': paginator,
        'page_num': page,
        'next_page': int(page) + 1,
        'prev_page': int(page) - 1,
        'num_pages': paginator.num_pages,
        'page': current_page,
    }, context_instance=RequestContext(request))


def list(request):
    featured = Project.objects.filter(featured=True)
    new = Project.objects.all().order_by('-created_on')[:4]
    active = Project.objects.get_popular(limit=4)

    def assign_counts(projects):
        for project in projects:
            project.followers_count = Relationship.objects.filter(
                target_project=project).count()

    assign_counts(featured)
    assign_counts(new)
    assign_counts(active)

    return render_to_response('projects/gallery.html', {
        'featured': featured,
        'new': new,
        'active': active,
    }, context_instance=RequestContext(request))


@login_required
def create(request):
    user = request.user.get_profile()
    if request.method == 'POST':
        form = project_forms.ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = user
            project.save()
            messages.success(request, _('Your new project has been created.'))
            return http.HttpResponseRedirect(reverse('projects_show', kwargs={
                'slug': project.slug,
            }))
        else:
            messages.error(request,
                _("There was a problem creating your project."))
    else:
        form = project_forms.ProjectForm()
    return render_to_response('projects/project_edit_summary.html', {
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
def contact_followers(request, slug):
    user = request.user.get_profile()
    project = get_object_or_404(Project, slug=slug)
    if project.created_by != user:
        return http.HttpResponseForbidden()
    if request.method == 'POST':
        form = project_forms.ProjectContactUsersForm(request.POST)
        if form.is_valid():
            form.save(sender=request.user)
            messages.info(request,
                          _("Message successfully sent."))
            return http.HttpResponseRedirect(reverse('projects_show', kwargs={
                'slug': project.slug,
            }))
    else:
        form = project_forms.ProjectContactUsersForm()
        form.fields['project'].initial = project.pk
    return render_to_response('projects/contact_users.html', {
        'form': form,
        'project': project,
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from relationships.models import Relationship

admin.site.register(Relationship)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Relationship'
        db.create_table('relationships_relationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='source_relationships', to=orm['users.UserProfile'])),
            ('target_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.UserProfile'], null=True, blank=True)),
            ('target_project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'], null=True, blank=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2011, 1, 22), auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('relationships', ['Relationship'])

        # Adding unique constraint on 'Relationship', fields ['source', 'target_user']
        db.create_unique('relationships_relationship', ['source_id', 'target_user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Relationship', fields ['source', 'target_user']
        db.delete_unique('relationships_relationship', ['source_id', 'target_user_id'])

        # Deleting model 'Relationship'
        db.delete_table('relationships_relationship')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'relationships.relationship': {
            'Meta': {'unique_together': "(('source', 'target_user'),)", 'object_name': 'Relationship'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_relationships'", 'to': "orm['users.UserProfile']"}),
            'target_project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True', 'blank': 'True'}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['relationships']

########NEW FILE########
__FILENAME__ = 0002_auto__add_unique_relationship_source_target_project
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Relationship', fields ['source', 'target_project']
        db.create_unique('relationships_relationship', ['source_id', 'target_project_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Relationship', fields ['source', 'target_project']
        db.delete_unique('relationships_relationship', ['source_id', 'target_project_id'])


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'relationships.relationship': {
            'Meta': {'unique_together': "(('source', 'target_user'), ('source', 'target_project'))", 'object_name': 'Relationship'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'source_relationships'", 'to': "orm['users.UserProfile']"}),
            'target_project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True', 'blank': 'True'}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True', 'blank': 'True'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['relationships']

########NEW FILE########
__FILENAME__ = models
import datetime
import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

from drumbeat.models import ModelBase
from activity.models import Activity
from preferences.models import AccountPreferences
from users.tasks import SendUserEmail

log = logging.getLogger(__name__)


class Relationship(ModelBase):
    """
    A relationship between two objects. Source is usually a user but can
    be any ```Model``` instance. Target can also be any ```Model``` instance.
    """
    source = models.ForeignKey(
        'users.UserProfile', related_name='source_relationships')
    target_user = models.ForeignKey(
        'users.UserProfile', null=True, blank=True)
    target_project = models.ForeignKey(
        'projects.Project', null=True, blank=True)

    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.date.today())

    def save(self, *args, **kwargs):
        """Check that the source and the target are not the same user."""
        if (self.source == self.target_user):
            raise ValidationError(
                _('Cannot create self referencing relationship.'))
        super(Relationship, self).save(*args, **kwargs)

    class Meta:
        unique_together = (
            ('source', 'target_user'),
            ('source', 'target_project'),
        )

    def __unicode__(self):
        return "%(from)r => %(to)r" % {
            'from': repr(self.source),
            'to': repr(self.target_user or self.target_project),
        }

###########
# Signals #
###########


def follow_handler(sender, **kwargs):
    rel = kwargs.get('instance', None)
    if not isinstance(rel, Relationship):
        return
    user_subject = _("%(name)s is following you on Drumbeat!" % {
        'name': rel.source.name,
    })
    project_subject = _("%(name)s is following your project on Drumbeat!" % {
        'name': rel.source.name,
    })
    activity = Activity(actor=rel.source,
                        verb='http://activitystrea.ms/schema/1.0/follow')
    subject = _(u"%(name)s is now following")
    if rel.target_user:
        activity.target_user = rel.target_user
        user = rel.target_user
        pref_key = 'no_email_new_follower'
        subject = user_subject
    else:
        activity.project = rel.target_project
        user = rel.target_project.created_by
        pref_key = 'no_email_new_project_follower'
        subject = project_subject
    activity.save()

    preferences = AccountPreferences.objects.filter(user=user)
    for pref in preferences:
        if pref.value and pref.key == pref_key:
            return

    body = render_to_string("relationships/emails/new_follower.txt", {
        'user': rel.source,
        'project': rel.target_project,
    })
    SendUserEmail.apply_async((user, subject, body))
post_save.connect(follow_handler, sender=Relationship)

########NEW FILE########
__FILENAME__ = tests
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from test_utils import TestCase

from activity.models import Activity
from activity.schema import verbs
from relationships.models import Relationship
from users.models import UserProfile
from projects.models import Project


class RelationshipsTests(TestCase):

    test_users = [
        dict(username='test_one', email='test_one@mozillafoundation.org'),
        dict(username='test_two', email='test_two@mozillafoundation.org'),
    ]

    def setUp(self):
        """Create data for testing."""
        for user in self.test_users:
            user = UserProfile(**user)
            user.set_password('testpass')
            user.save()
            user.create_django_user()
        (self.user_one, self.user_two) = UserProfile.objects.all()

    def test_unidirectional_user_relationship(self):
        """Test a one way relationship between two users."""
        # User 1 follows User 2
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_two,
        )
        relationship.save()
        self.assertEqual(self.user_one.following(), [self.user_two])

    def test_unique_user_constraint(self):
        """Test that a user can't follow another user twice."""
        # User 1 follows User 2
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_two,
        )
        relationship.save()

        # Try again
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_two,
        )
        self.assertRaises(IntegrityError, relationship.save)

    def test_unique_project_constraint(self):
        """Test that a user can't follow the same project twice."""
        project = Project(
            name='test project',
            short_description='for testing',
            long_description='for testing relationships',
            created_by=self.user_one,
        )
        project.save()

        # creator will automatically be following the project
        relationships = Relationship.objects.all()
        self.assertEqual(relationships[0].source, self.user_one)
        self.assertEqual(relationships[0].target_project, project)

        relationship = Relationship(
            source=self.user_one,
            target_project=project,
        )
        self.assertRaises(IntegrityError, relationship.save)

    def test_narcissistic_user(self):
        """Test that one cannot follow oneself."""
        relationship = Relationship(
            source=self.user_one,
            target_user=self.user_one,
        )
        self.assertRaises(ValidationError, relationship.save)

    def test_bidirectional_relationship(self):
        """Test symmetric relationship."""
        Relationship(source=self.user_one, target_user=self.user_two).save()
        Relationship(source=self.user_two, target_user=self.user_one).save()

        rels_one = self.user_one.following()
        rels_two = self.user_two.following()

        self.assertTrue(self.user_one in rels_two)
        self.assertTrue(self.user_two not in rels_two)
        self.assertTrue(self.user_two in rels_one)
        self.assertTrue(self.user_one not in rels_one)

    def test_user_followers(self):
        """Test the followers method of the User model."""
        self.assertTrue(len(self.user_two.followers()) == 0)
        Relationship(source=self.user_one, target_user=self.user_two).save()
        self.assertTrue(len(self.user_two.followers()) == 1)
        self.assertEqual(self.user_one, self.user_two.followers()[0])

    def test_user_following(self):
        """Test the following method of the User model."""
        self.assertTrue(len(self.user_one.following()) == 0)
        Relationship(source=self.user_one, target_user=self.user_two).save()
        self.assertTrue(len(self.user_one.following()) == 1)
        self.assertEqual(self.user_two, self.user_one.following()[0])

    def test_user_is_following(self):
        """Test the is_following method of the User model."""
        self.assertFalse(self.user_one.is_following(self.user_two))
        Relationship(source=self.user_one, target_user=self.user_two).save()
        self.assertTrue(self.user_one.is_following(self.user_two))

    def test_activity_creation(self):
        """Test that an activity is created when a relationship is created."""
        self.assertEqual(0, Activity.objects.count())
        Relationship(source=self.user_one, target_user=self.user_two).save()
        activities = Activity.objects.all()
        self.assertEqual(1, len(activities))
        activity = activities[0]
        self.assertEqual(self.user_one, activity.actor)
        self.assertEqual(self.user_two, activity.target_user)
        self.assertEqual(verbs['follow'], activity.verb)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^follow/(?P<object_type>[\w-]+)/(?P<slug>[\w\-\. ]+)/$',
        'relationships.views.follow',
        name='relationships_follow'),
    url(r'^unfollow/(?P<object_type>[\w-]+)/(?P<slug>[\w\-\. ]+)/$',
        'relationships.views.unfollow',
        name='relationships_unfollow'),
)

########NEW FILE########
__FILENAME__ = views
import logging

from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from relationships.models import Relationship
from projects.models import Project
from users.models import UserProfile
from users.decorators import login_required

from drumbeat import messages

log = logging.getLogger(__name__)


@login_required
@require_http_methods(['POST'])
def follow(request, object_type, slug):
    profile = request.user.get_profile()
    if object_type == 'project':
        project = get_object_or_404(Project, slug=slug)
        relationship = Relationship(source=profile, target_project=project)
    elif object_type == 'user':
        user = get_object_or_404(UserProfile, username=slug)
        relationship = Relationship(source=profile, target_user=user)
    else:
        raise Http404
    try:
        relationship.save()
    except IntegrityError:
        if object_type == 'project':
            messages.error(
                request, _('You are already following this project'))
        else:
            messages.error(request, _('You are already following this user'))
        log.warn("Attempt to create duplicate relationship: %s" % (
            relationship,))
    return HttpResponseRedirect(request.META['HTTP_REFERER'])


@login_required
@require_http_methods(['POST'])
def unfollow(request, object_type, slug):
    profile = request.user.get_profile()
    if object_type == 'project':
        project = get_object_or_404(Project, slug=slug)
        if project.created_by == profile:
            return HttpResponseForbidden()
        Relationship.objects.filter(
            source=profile, target_project=project).delete()
    elif object_type == 'user':
        user = get_object_or_404(UserProfile, username=slug)
        Relationship.objects.filter(
            source=profile, target_user=user).delete()
    else:
        raise Http404
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

########NEW FILE########
__FILENAME__ = forms
from django import forms

from statuses.models import Status


class StatusForm(forms.ModelForm):

    class Meta:
        model = Status
        fields = ('project', 'status', 'in_reply_to')

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Status'
        db.create_table('statuses_status', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('statuses', ['Status'])


    def backwards(self, orm):
        
        # Deleting model 'Status'
        db.delete_table('statuses_status')


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
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_status_project
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Status.project'
        db.add_column('statuses_status', 'project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['projects.Project'], null=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Status.project'
        db.delete_column('statuses_status', 'project_id')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0003_auto__del_field_status_timestamp__add_field_status_created_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Status.timestamp'
        db.delete_column('statuses_status', 'timestamp')

        # Adding field 'Status.created_on'
        db.add_column('statuses_status', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 11, 29), auto_now_add=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Status.timestamp'
        db.add_column('statuses_status', 'timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.date(2010, 11, 29), blank=True), keep_default=False)

        # Deleting field 'Status.created_on'
        db.delete_column('statuses_status', 'created_on')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 11, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 11, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '1024'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_status_status
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Status.status'
        db.alter_column('statuses_status', 'status', self.gf('django.db.models.fields.CharField')(max_length=750))


    def backwards(self, orm):
        
        # Changing field 'Status.status'
        db.alter_column('statuses_status', 'status', self.gf('django.db.models.fields.CharField')(max_length=1024))


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 7)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 7)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_status_author
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Status.author'
        db.alter_column('statuses_status', 'author_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['users.UserProfile']))


    def backwards(self, orm):
        
        # Changing field 'Status.author'
        db.alter_column('statuses_status', 'author_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'call_to_action': ('django.db.models.fields.TextField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'css': ('django.db.models.fields.TextField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'template': ('django.db.models.fields.TextField', [], {})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_status_in_reply_to
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Status.in_reply_to'
        db.add_column('statuses_status', 'in_reply_to', self.gf('django.db.models.fields.related.ForeignKey')(related_name='replies', null=True, to=orm['statuses.Status']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Status.in_reply_to'
        db.delete_column('statuses_status', 'in_reply_to_id')


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
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 15)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 15)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'replies'", 'null': 'True', 'to': "orm['statuses.Status']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 15)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_status_in_reply_to
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Changing field 'Status.in_reply_to'
        db.alter_column('statuses_status', 'in_reply_to_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['activity.Activity']))


    def backwards(self, orm):
        
        # Changing field 'Status.in_reply_to'
        db.alter_column('statuses_status', 'in_reply_to_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['statuses.Status']))


    models = {
        'activity.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.Activity']", 'null': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'remote_object': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['activity.RemoteObject']", 'null': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['statuses.Status']", 'null': 'True'}),
            'target_project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_project'", 'null': 'True', 'to': "orm['projects.Project']"}),
            'target_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'target_user'", 'null': 'True', 'to': "orm['users.UserProfile']"}),
            'verb': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'activity.remoteobject': {
            'Meta': {'object_name': 'RemoteObject'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['links.Link']"}),
            'object_type': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uri': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'})
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
        },
        'links.link': {
            'Meta': {'object_name': 'Link'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscriber.Subscription']", 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']", 'null': 'True'})
        },
        'projects.project': {
            'Meta': {'object_name': 'Project'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects'", 'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_description': ('django.db.models.fields.TextField', [], {}),
            'detailed_description_html': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'long_description': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '125'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'statuses.status': {
            'Meta': {'object_name': 'Status'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.UserProfile']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['activity.Activity']"}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['projects.Project']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '750'})
        },
        'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 3, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['statuses']

########NEW FILE########
__FILENAME__ = models
import datetime
from markdown import markdown
from bleach import Bleach

from django.contrib import admin
from django.db import models
from django.db.models.signals import post_save
from django.utils.timesince import timesince
from django.utils.html import urlize

from activity.models import Activity
from drumbeat.models import ModelBase

TAGS = ('a', 'b', 'em', 'i', 'strong', 'p')


class Status(ModelBase):
    object_type = 'http://activitystrea.ms/schema/1.0/status'

    author = models.ForeignKey('users.UserProfile')
    project = models.ForeignKey('projects.Project', null=True, blank=True)
    status = models.CharField(max_length=750)
    in_reply_to = models.ForeignKey(Activity, related_name='replies',
                                    null=True, blank=True)
    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.date.today())

    def __unicode__(self):
        return self.status

    @models.permalink
    def get_absolute_url(self):
        return ('statuses_show', (), {
            'status_id': self.pk,
        })

    def timesince(self, now=None):
        return timesince(self.created_on, now)

admin.site.register(Status)


def status_creation_handler(sender, **kwargs):
    status = kwargs.get('instance', None)
    created = kwargs.get('created', False)

    if not created or not isinstance(status, Status):
        return

    # convert status body to markdown and bleachify
    bl = Bleach()
    status.status = urlize(status.status)
    status.status = bl.clean(markdown(status.status), tags=TAGS)
    status.save()

    # fire activity
    activity = Activity(
        actor=status.author,
        verb='http://activitystrea.ms/schema/1.0/post',
        status=status,
    )
    if status.project:
        activity.target_project = status.project
    if status.in_reply_to:
        activity.parent = status.in_reply_to
    activity.save()
post_save.connect(status_creation_handler, sender=Status)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
  url(r'^(?P<status_id>\d+)/$', 'statuses.views.show',
      name='statuses_show'),
  url(r'^create/$', 'statuses.views.create',
      name='statuses_create'),
  url(r'^create/project/(?P<project_id>\d+)/$',
      'statuses.views.create_project_status',
      name='statuses_create_project'),
)

########NEW FILE########
__FILENAME__ = views
import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from activity.models import Activity
from statuses.forms import StatusForm
from statuses.models import Status
from projects.models import Project
from users.decorators import login_required

from drumbeat import messages

log = logging.getLogger(__name__)


def show(request, status_id):
    status = get_object_or_404(Status, id=status_id)
    return render_to_response('statuses/show.html', {
        'status': status,
    }, context_instance=RequestContext(request))


@login_required
def create(request):
    if request.method != 'POST' or 'status' not in request.POST:
        return HttpResponseRedirect('/')
    form = StatusForm(data=request.POST)
    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user.get_profile()
        status.save()
    else:
        log.debug("form error: %s" % (str(form.errors)))
        messages.error(request, _('There was an error posting '
                                  'your status update'))
    return HttpResponseRedirect('/')


@login_required
def reply(request, in_reply_to):
    """Create a status update that is a reply to an activity."""
    parent = get_object_or_404(Activity, id=in_reply_to)
    if request.method == 'POST':
        form = StatusForm(data=request.POST)
        if form.is_valid():
            status = form.save(commit=False)
            status.author = request.user.get_profile()
            status.in_reply_to = parent
            status.save()
        return HttpResponseRedirect('/')
    return render_to_response('statuses/reply.html', {
        'parent': parent,
    }, context_instance=RequestContext(request))


@login_required
def create_project_status(request, project_id):
    if request.method != 'POST' or 'status' not in request.POST:
        return HttpResponseRedirect('/')
    project = get_object_or_404(Project, id=project_id)
    profile = request.user.get_profile()
    form = StatusForm(data=request.POST)
    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user.get_profile()
        status.project = project
        status.save()
        log.debug("Saved status by user (%d) to project (%d): %s" % (
            profile.id, project.id, status))
    else:
        messages.error(request, _('There was an error posting '
                                  'your status update'))
    return HttpResponseRedirect(
        reverse('projects_show', kwargs=dict(slug=project.slug)))

########NEW FILE########
__FILENAME__ = backends
import logging

from django.contrib.auth.models import User

from users.models import UserProfile

log = logging.getLogger(__name__)


class CustomUserBackend(object):
    supports_anonymous_user = False
    supports_object_permissions = False

    def authenticate(self, username=None, password=None):
        log.debug("Attempting to authenticate user %s" % (username,))
        try:
            if '@' in username:
                profile = UserProfile.objects.get(email=username)
            else:
                profile = UserProfile.objects.get(username=username)
            if profile.check_password(password):
                if profile.user is None:
                    profile.create_django_user()
                return profile.user
        except UserProfile.DoesNotExist:
            log.debug("User does not exist: %s" % (username,))
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = blacklist
# a list of passwords that meet our policy requirements (at least 8 characters
# and alphanumeric) but are still common and easily guessed.
# TODO - Find a definitive source for this
passwords = (
    'trustno1',
    'access14',
    'rush2112',
    'p@$$w0rd',
    'abcd1234',
    'qwerty123',
)

########NEW FILE########
__FILENAME__ = context_processors
from django.utils.http import urlquote
from django.contrib.auth import REDIRECT_FIELD_NAME

from messages.models import Message
from l10n.urlresolvers import reverse


def messages(request):
    if request.user.is_authenticated():
        messages = Message.objects.select_related('sender').filter(
            recipient=request.user,
            recipient_deleted_at__isnull=True)[:3]
        return {'preview_messages': messages}
    else:
        return {}


def redirect_urls(request):
    path = urlquote(request.get_full_path())
    login_url = '%s?%s=%s' % (
        reverse('users_login'), REDIRECT_FIELD_NAME, path)
    register_url = '%s?%s=%s' % (
        reverse('users_register'), REDIRECT_FIELD_NAME, path)
    return {
        'login_with_redirect_url': login_url,
        'register_with_redirect_url': register_url,
    }

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.utils.decorators import available_attrs

from drumbeat import messages
from users.models import UserProfile


def anonymous_only(func):
    """
    Opposite of ``django.contrib.auth.decorators.login_required``. This
    decorator is for views that redirect users to the redirect field name
    if they are already logged in.
    """

    def decorator(*args, **kwargs):
        request = args[0]
        if request.user.is_authenticated():
            messages.info(request,
                          _("You are already logged into an account."))
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return func(*args, **kwargs)
    return decorator


def user_passes_test(test_func):
    """
    Custom user_passes_test that punts login url redirecting to the
    dashboard_index view.
    """

    def decorator(view_func):

        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            return HttpResponseRedirect(reverse('dashboard_index'))
        return wraps(view_func,
                     assigned=available_attrs(view_func))(_wrapped_view)
    return decorator


def login_required(func=None, profile_required=True):
    """
    Custom implementation of ``django.contrib.auth.decorators.login_required``.
    This version has an optional parameter, ``profile_required`` which, if
    True, will check that a user is both authenticated and has a profile. This
    is useful so that the create profile page can load successfully, but a user
    will still be locked out of other views.
    """
    if profile_required:
        test = lambda u: (u.is_authenticated() and
                          len(UserProfile.objects.filter(user=u)) > 0)
    else:
        test = lambda u: u.is_authenticated()
    actual_decorator = user_passes_test(test)
    if func:
        return actual_decorator(func)
    return actual_decorator

########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.core import urlresolvers
from drumbeat.utils import slug_validator
from django.utils.translation import ugettext_lazy as _


class UsernameField(forms.Field):
    widget = forms.widgets.TextInput(attrs={'autocomplete': 'off'})

    def clean(self, value):
        super(UsernameField, self).clean(value)
        slug_validator(value, lower=False)
        try:
            func, args, kwargs = urlresolvers.resolve("/%s/" % (value,))
            if callable(func) and args == ():
                if 'username' not in kwargs.keys():
                    raise forms.ValidationError(
                        _('Please choose another username.'))
        except urlresolvers.Resolver404:
            pass
        return value

########NEW FILE########
__FILENAME__ = forms
import re

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import forms as auth_forms
from django.utils.translation import ugettext as _

from captcha import fields as captcha_fields

from users.blacklist import passwords as blacklisted_passwords
from users.models import UserProfile
from users.fields import UsernameField


class AuthenticationForm(auth_forms.AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'tabindex': '1'}))
    password = forms.CharField(
        max_length=255,
        widget=forms.PasswordInput(attrs={'tabindex': '2'},
                                   render_value=False))
    remember_me = forms.BooleanField(required=False,
                                     widget=forms.CheckboxInput(
                                         attrs={'tabindex': '3'}))


def check_password_complexity(password):
    message = _('Password must be at least 8 ' +
                'characters long and contain ' +
                'both numbers and letters')
    if len(password) < 8 or not (
        re.search('[A-Za-z]', password) and re.search('[0-9]', password)):
        return message
    if password in blacklisted_passwords:
        return _('That password is too common. Please choose another.')
    return None


class SetPasswordForm(auth_forms.SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super(SetPasswordForm, self).__init__(*args, **kwargs)

        # make sure to set the password in the user profile
        if isinstance(self.user, User):
            self.user = self.user.get_profile()

    def clean_new_password1(self):
        password = self.cleaned_data['new_password1']
        message = check_password_complexity(password)
        if message:
            self._errors['new_password1'] = forms.util.ErrorList([message])
        return password


class OpenIDForm(forms.Form):
    openid_identifier = forms.URLField(
        widget=forms.TextInput(attrs={
            'placeholder': _('enter any OpenID URL')}))


class CreateProfileForm(forms.ModelForm):
    recaptcha = captcha_fields.ReCaptchaField()

    class Meta:
        model = UserProfile
        fields = ('username', 'display_name',
                  'bio', 'image', 'newsletter', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super(CreateProfileForm, self).__init__(*args, **kwargs)

        if not settings.RECAPTCHA_PRIVATE_KEY:
            del self.fields['recaptcha']


class RegisterForm(forms.ModelForm):
    username = UsernameField()
    password = forms.CharField(
        max_length=255,
        widget=forms.PasswordInput(render_value=False))
    password_confirm = forms.CharField(
        max_length=255,
        widget=forms.PasswordInput(render_value=False))
    recaptcha = captcha_fields.ReCaptchaField()

    class Meta:
        model = UserProfile
        widgets = {
            'username': forms.TextInput(attrs={'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)

        if not settings.RECAPTCHA_PRIVATE_KEY:
            del self.fields['recaptcha']

    def clean_password(self):
        password = self.cleaned_data['password']
        message = check_password_complexity(password)
        if message:
            self._errors['password'] = forms.util.ErrorList([message])
        return password

    def clean(self):
        """Ensure password and password_confirm match."""
        super(RegisterForm, self).clean()
        data = self.cleaned_data
        if 'password' in data and 'password_confirm' in data:
            if data['password'] != data['password_confirm']:
                self._errors['password_confirm'] = forms.util.ErrorList([
                    _('Passwords do not match.')])
        return data


class ProfileEditForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        exclude = ('confirmation_code', 'password', 'username', 'email',
                   'created_on', 'user', 'image', 'featured')


class ProfileImageForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        exclude = ('confirmation_code', 'password', 'username',
                   'email', 'created_on', 'user', 'featured')

    def clean_image(self):
        if self.cleaned_data['image'].size > settings.MAX_IMAGE_SIZE:
            max_size = settings.MAX_IMAGE_SIZE / 1024
            raise forms.ValidationError(
                _("Image exceeds max image size: %(max)dk") % dict(
                    max=max_size))
        return self.cleaned_data['image']

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ConfirmationToken'
        db.create_table('users_confirmationtoken', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('users', ['ConfirmationToken'])


    def backwards(self, orm):
        
        # Deleting model 'ConfirmationToken'
        db.delete_table('users_confirmationtoken')


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
        'users.confirmationtoken': {
            'Meta': {'object_name': 'ConfirmationToken'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_confirmationtoken_created_on
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ConfirmationToken.created_on'
        db.add_column('users_confirmationtoken', 'created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 11, 29), auto_now_add=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ConfirmationToken.created_on'
        db.delete_column('users_confirmationtoken', 'created_on')


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
        'users.confirmationtoken': {
            'Meta': {'object_name': 'ConfirmationToken'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 11, 29)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0003_auto__add_userprofile
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'UserProfile'
        db.create_table('users_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('username', self.gf('django.db.models.fields.CharField')(default='', unique=True, max_length=255)),
            ('display_name', self.gf('django.db.models.fields.CharField')(default='', max_length=255, null=True, blank=True)),
            ('password', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, unique=True, null=True)),
            ('bio', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('confirmation_code', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('location', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 12, 16), auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
        ))
        db.send_create_signal('users', ['UserProfile'])


    def backwards(self, orm):
        
        # Deleting model 'UserProfile'
        db.delete_table('users_userprofile')


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
        'users.confirmationtoken': {
            'Meta': {'object_name': 'ConfirmationToken'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0004_auto__add_field_userprofile_image
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.image'
        db.add_column('users_userprofile', 'image', self.gf('django.db.models.fields.files.ImageField')(default='', max_length=100, null=True, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.image'
        db.delete_column('users_userprofile', 'image')


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
        'users.confirmationtoken': {
            'Meta': {'object_name': 'ConfirmationToken'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 16)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0005_auto__del_confirmationtoken__add_taggedprofile__add_profiletag__chg_fi
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting model 'ConfirmationToken'
        db.delete_table('users_confirmationtoken')

        # Adding model 'TaggedProfile'
        db.create_table('users_taggedprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='users_taggedprofile_tagged_items', to=orm['contenttypes.ContentType'])),
            ('tag', self.gf('django.db.models.fields.related.ForeignKey')(related_name='users_taggedprofile_items', to=orm['users.ProfileTag'])),
        ))
        db.send_create_signal('users', ['TaggedProfile'])

        # Adding model 'ProfileTag'
        db.create_table('users_profiletag', (
            ('tag_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['taggit.Tag'], unique=True, primary_key=True)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=10)),
        ))
        db.send_create_signal('users', ['ProfileTag'])

        # Changing field 'UserProfile.image'
        db.alter_column('users_userprofile', 'image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True))


    def backwards(self, orm):
        
        # Adding model 'ConfirmationToken'
        db.create_table('users_confirmationtoken', (
            ('created_on', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 12, 16), auto_now_add=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('users', ['ConfirmationToken'])

        # Deleting model 'TaggedProfile'
        db.delete_table('users_taggedprofile')

        # Deleting model 'ProfileTag'
        db.delete_table('users_profiletag')

        # Changing field 'UserProfile.image'
        db.alter_column('users_userprofile', 'image', self.gf('django.db.models.fields.files.ImageField')(max_length=100))


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
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 18)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_userprofile_featured
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.featured'
        db.add_column('users_userprofile', 'featured', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.featured'
        db.delete_column('users_userprofile', 'featured')


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
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2010, 12, 22)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_userprofile_newsletter
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.newsletter'
        db.add_column('users_userprofile', 'newsletter', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.newsletter'
        db.delete_column('users_userprofile', 'newsletter')


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
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 1, 5)', 'auto_now_add': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_userprofile_discard_welcome
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'UserProfile.discard_welcome'
        db.add_column('users_userprofile', 'discard_welcome', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'UserProfile.discard_welcome'
        db.delete_column('users_userprofile', 'discard_welcome')


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
        'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'users.profiletag': {
            'Meta': {'object_name': 'ProfileTag', '_ormbases': ['taggit.Tag']},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['taggit.Tag']", 'unique': 'True', 'primary_key': 'True'})
        },
        'users.taggedprofile': {
            'Meta': {'object_name': 'TaggedProfile'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_tagged_items'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'users_taggedprofile_items'", 'to': "orm['users.ProfileTag']"})
        },
        'users.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'bio': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'confirmation_code': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.date(2011, 2, 7)', 'auto_now_add': 'True', 'blank': 'True'}),
            'discard_welcome': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'unique': 'True', 'null': 'True'}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'default': "''", 'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'newsletter': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'password': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'default': "''", 'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['users']

########NEW FILE########
__FILENAME__ = models
import logging
import datetime
import random
import string
import hashlib
import os

from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from taggit.models import GenericTaggedItemBase, Tag
from taggit.managers import TaggableManager

from drumbeat import storage
from drumbeat.utils import get_partition_id, safe_filename
from drumbeat.models import ModelBase
from relationships.models import Relationship
from projects.models import Project
from users import tasks

import caching.base

log = logging.getLogger(__name__)


def determine_upload_path(instance, filename):
    chunk_size = 1000  # max files per directory
    return "images/profiles/%(partition)d/%(filename)s" % {
        'partition': get_partition_id(instance.pk, chunk_size),
        'filename': safe_filename(filename),
    }


def get_hexdigest(algorithm, salt, raw_password):
    """Generate password hash."""
    return hashlib.new(algorithm, smart_str(salt + raw_password)).hexdigest()


def create_password(algorithm, raw_password):
    """Create salted, hashed password."""
    salt = os.urandom(5).encode('hex')
    hsh = get_hexdigest(algorithm, salt, raw_password)
    return '$'.join((algorithm, salt, hsh))


class ProfileTag(Tag):
    CATEGORY_CHOICES = (
        ('skill', 'Skill'),
        ('interest', 'Interest'),
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)


class TaggedProfile(GenericTaggedItemBase):
    tag = models.ForeignKey(
        ProfileTag, related_name="%(app_label)s_%(class)s_items")

    class Meta:
        verbose_name = "Tagged User Profile"
        verbose_name_plural = "Tagged User Profiles"


class UserProfileManager(caching.base.CachingManager):

    def get_popular(self, limit=0):
        users = Relationship.objects.values('target_user_id').annotate(
            models.Count('id')).filter(target_user__featured=False).order_by(
            '-id__count')[:limit]
        user_ids = [u['target_user_id'] for u in users]
        return UserProfile.objects.filter(id__in=user_ids)


class UserProfile(ModelBase):
    """Each user gets a profile."""
    object_type = 'http://activitystrea.ms/schema/1.0/person'

    username = models.CharField(max_length=255, default='', unique=True)
    display_name = models.CharField(
        max_length=255, default='', null=True, blank=True)
    password = models.CharField(max_length=255, default='')
    email = models.EmailField(unique=True, null=True)
    bio = models.TextField(blank=True, default='')
    image = models.ImageField(
        upload_to=determine_upload_path, default='', blank=True, null=True,
        storage=storage.ImageStorage())
    confirmation_code = models.CharField(
        max_length=255, default='', blank=True)
    location = models.CharField(max_length=255, blank=True, default='')
    featured = models.BooleanField()
    newsletter = models.BooleanField()
    discard_welcome = models.BooleanField(default=False)
    created_on = models.DateTimeField(
        auto_now_add=True, default=datetime.date.today())

    user = models.ForeignKey(User, null=True, editable=False, blank=True)
    tags = TaggableManager(through=TaggedProfile)

    objects = UserProfileManager()

    def __unicode__(self):
        return self.display_name or self.username

    def following(self, model=None):
        """
        Return a list of objects this user is following. All objects returned
        will be ```Project``` or ```UserProfile``` instances. Optionally filter
        by type by including a ```model``` parameter.
        """
        if (model == 'Project' or isinstance(model, Project) or
            model == Project):
            relationships = Relationship.objects.select_related(
                'target_project').filter(source=self).exclude(
                target_project__isnull=True)
            return [rel.target_project for rel in relationships]
        relationships = Relationship.objects.select_related(
            'target_user').filter(source=self).exclude(
            target_user__isnull=True)
        return [rel.target_user for rel in relationships]

    def followers(self):
        """Return a list of this users followers."""
        relationships = Relationship.objects.select_related(
            'source').filter(target_user=self)
        return [rel.source for rel in relationships]

    def is_following(self, model):
        """Determine whether this user is following ```model```."""
        return model in self.following(model=model)

    @models.permalink
    def get_absolute_url(self):
        return ('users_profile_view', (), {
            'username': self.username,
        })

    def create_django_user(self):
        """Make a django.contrib.auth.models.User for this UserProfile."""
        self.user = User(id=self.pk)
        self.user.username = self.username
        self.user.email = self.email
        self.user.date_joined = self.created_on
        self.user.backend = 'django.contrib.auth.backends.ModelBackend'
        self.user.save()
        self.save()
        return self.user

    def email_confirmation_code(self, url):
        """Send a confirmation email to the user after registering."""
        body = render_to_string('users/emails/registration_confirm.txt', {
            'confirmation_url': url,
        })
        subject = _('Complete Registration')
        tasks.SendUserEmail.apply_async(args=(self, subject, body))

    def image_or_default(self):
        """Return user profile image or a default."""
        return self.image or 'images/member-missing.png'

    def generate_confirmation_code(self):
        if not self.confirmation_code:
            self.confirmation_code = ''.join(random.sample(string.letters +
                                                           string.digits, 60))
        return self.confirmation_code

    def set_password(self, raw_password, algorithm='sha512'):
        self.password = create_password(algorithm, raw_password)

    def check_password(self, raw_password):
        if '$' not in self.password:
            valid = (get_hexdigest('md5', '', raw_password) == self.password)
            if valid:
                # Upgrade an old password.
                self.set_password(raw_password)
                self.save()
            return valid

        algo, salt, hsh = self.password.split('$')
        return hsh == get_hexdigest(algo, salt, raw_password)

    @property
    def name(self):
        return self.display_name or self.username
admin.site.register(UserProfile)

########NEW FILE########
__FILENAME__ = tasks
import datetime

from celery.task import Task

from messages.models import Message


class SendUserEmail(Task):
    """Send an email to a specific user specified by ``profile``."""

    def run(self, profile, subject, body, **kwargs):
        log = self.get_logger(**kwargs)
        log.debug("Sending email to user %d with subject %s" % (
            profile.user.id, subject,))
        profile.user.email_user(subject, body)


class SendUsersEmail(Task):
    """
    Send an email to multiple users. ``messages`` should be a sequence
    containing tuples of sender, recipient, subject, body, parent.
    """

    def run(self, form, messages, **kwargs):
        log = self.get_logger(**kwargs)
        log.debug("Sending email to %d user(s)." % (len(messages),))
        for message in messages:
            (sender, recipient, subject, body, parent) = message
            msg = Message(sender=sender, recipient=recipient,
                          subject=subject, body=body)
            if parent is not None:
                msg.parent_msg = parent
                parent.replied_at = datetime.datetime.now()
                parent.save()
            msg.save()

########NEW FILE########
__FILENAME__ = tests
from django.test import Client
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse

from drumbeat.utils import get_partition_id
from users.models import UserProfile

from test_utils import TestCase


class TestLogins(TestCase):

    test_username = 'testuser'
    test_password = 'testpassword'
    test_email = 'test@mozillafoundation.org'

    def setUp(self):
        self.locale = 'en-US'
        self.client = Client()
        self.user = UserProfile(username=self.test_username,
                                email=self.test_email)
        self.user.set_password(self.test_password)
        self.user.save()
        self.user.create_django_user()

    def test_authenticated_redirects(self):
        """Test that authenticated users are redirected in specific views."""
        self.client.login(username=self.test_username,
                          password=self.test_password)
        paths = ('login/', 'register/',
                 'confirm/123456/username/',
                 'confirm/resend/username/')
        for path in paths:
            full = "/%s/%s" % (self.locale, path)
            response = self.client.get(full)
            print response
            self.assertRedirects(response, '/', status_code=302,
                                 target_status_code=301)
        self.client.logout()

    def test_unauthenticated_redirects(self):
        """Test that anonymous users are redirected for specific views."""
        paths = ('logout/', 'profile/edit/', 'profile/edit/image/')
        for path in paths:
            full = "/%s/%s" % (self.locale, path)
            response = self.client.get(full)
            expected = "/%s/" % (self.locale,)
            self.assertRedirects(response, expected, status_code=302,
                                 target_status_code=200)

    def test_login_post(self):
        """Test logging in."""
        path = "/%s/login/" % (self.locale,)
        response = self.client.post(path, {
            'username': self.test_username,
            'password': self.test_password,
        })
        self.assertRedirects(response, '/', status_code=302,
                             target_status_code=301)
        # TODO - Improve this so it doesn't take so many redirects to get a 200
        response2 = self.client.get(response["location"])
        response3 = self.client.get(response2["location"])
        response4 = self.client.get(response3["location"])
        self.assertContains(response4, 'id="dashboard"')
        self.client.logout()

        response5 = self.client.post(path, {
            'username': 'nonexistant',
            'password': 'password',
        })
        self.assertContains(response5, 'id="id_username"')

    def test_login_redirect_param(self):
        """Test that user is redirected properly after logging in."""
        path = "/%s/login/?%s=/%s/profile/edit/" % (
            self.locale, REDIRECT_FIELD_NAME, self.locale)
        response = self.client.post(path, {
            'username': self.test_username,
            'password': self.test_password,
        })
        self.assertEqual(
            "http://testserver/%s/profile/edit/" % (self.locale,),
            response["location"],
        )

    def test_login_redirect_param_header_injection(self):
        """
        Test that we can't inject headers into response with redirect param.
        """
        path = "/%s/login/" % (self.locale,)
        redirect_param = "foo\r\nLocation: http://example.com"
        response = self.client.post(path + "?%s=%s" % (
            REDIRECT_FIELD_NAME, redirect_param), {
            'username': self.test_username,
            'password': self.test_password,
        })
        self.assertNotEqual('http://example.com', response['location'])

    def test_redirect_param_outside_site(self):
        """
        Test that redirect parameter cannot be used as an open redirector.
        """
        path = "/%s/login/" % (self.locale,)
        redirect_param = "http://www.mozilla.org/"
        response = self.client.post(path + "?%s=%s" % (
            REDIRECT_FIELD_NAME, redirect_param), {
            'username': self.test_username,
            'password': self.test_password,
        })
        self.assertNotEqual('http://www.mozilla.org/', response['location'])

    def test_profile_image_directories(self):
        """Test that we partition image directories properly."""
        for i in range(1, 1001):
            p_id = get_partition_id(i)
            self.assertEqual(1, p_id)
        for i in range(1001, 2001):
            p_id = get_partition_id(i)
            self.assertEqual(2, p_id)
        for i in range(10001, 11001):
            p_id = get_partition_id(i)
            self.assertEqual(11, p_id)
        self.assertEqual(12, get_partition_id(11002))

    def test_protected_usernames(self):
        """
        Ensure that users cannot register using usernames that would conflict
        with other urlpatterns.
        """
        path = reverse('users_register')
        bad = ('projects', 'admin', 'people', 'events')
        for username in bad:
            response = self.client.post(path, {
                'username': username,
                'password': 'foobar123',
                'password_confirm': 'foobar123',
                'email': 'foobar123@example.com',
            })
            self.assertContains(response, 'Please choose another')
        ok = self.client.post(path, {
            'username': 'iamtrulyunique',
            'password': 'foobar123',
            'password_confirm': 'foobar123',
            'email': 'foobar123@example.com',
        })
        self.assertEqual(302, ok.status_code)

    def test_check_username_uniqueness(self):
        path = "/ajax/check_username/"
        existing = self.client.get(path, {
            'username': self.test_username,
        })
        self.assertEqual(200, existing.status_code)
        notfound = self.client.get(path, {
            'username': 'butterfly',
        })
        self.assertEqual(404, notfound.status_code)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from users import forms

urlpatterns = patterns('',

  # Login / auth urls
  url(r'^login/$', 'users.views.login',
      name='users_login'),
  url(r'^login/openid/$', 'users.views.login_openid',
      name='users_login_openid'),
  url(r'^login/openid/complete/$', 'users.views.login_openid_complete',
      name='users_login_openid_complete'),
  url(r'^logout/', 'users.views.logout',
      name='users_logout'),

  # Reset password urls
  url(r'^forgot/$',
      'django.contrib.auth.views.password_reset',
      {'template_name': 'users/forgot_password.html',
       'email_template_name': 'users/emails/forgot_password.txt'},
      name='users_forgot_password'),

  url(r'^forgot/sent/$',
      'django.contrib.auth.views.password_reset_done',
      {'template_name': 'users/forgot_password_done.html'},
      name='users_forgot_password_done'),

  url(r'^forgot/(?P<uidb36>\w{1,13})/(?P<token>\w{1,13}-\w{1,20})/$',
      'django.contrib.auth.views.password_reset_confirm',
      {'template_name': 'users/forgot_password_confirm.html',
       'set_password_form': forms.SetPasswordForm},
      name='users_forgot_password_confirm'),

  url(r'^forgot/complete/$',
      'django.contrib.auth.views.password_reset_complete',
      {'template_name': 'users/forgot_password_complete.html'},
      name='users_forgot_password_complete'),


  # Public pages
  url(r'^people/', 'users.views.user_list',
      name='users_user_list'),

  # Registration urls
  url(r'^register/$', 'users.views.register',
      name='users_register'),
  url(r'^register/openid/$', 'users.views.register_openid',
      name='users_register_openid'),
  url(r'^confirm/resend/(?P<username>[\w\-\. ]+)/$',
      'users.views.confirm_resend',
      name='users_confirm_resend'),
  url(r'^confirm/(?P<token>\w+)/(?P<username>[\w\-\. ]+)/$',
      'users.views.confirm_registration',
      name='users_confirm_registration'),
  url(r'^register/openid/complete/$', 'users.views.register_openid_complete',
      name='users_register_openid_complete'),

  # Ajax handlers
  url(r'^ajax/check_username/$', 'users.views.check_username',
      name='users_check_username'),
  url(r'^ajax/following/$', 'users.views.following',
      name='users_followers'),

  # Profile urls
  url(r'^(?P<username>[\w\-\. ]+)/$', 'users.views.profile_view',
      name='users_profile_view'),
  url(r'^profile/edit/$', 'users.views.profile_edit',
      name='users_profile_edit'),
  url(r'^profile/edit/image/$', 'users.views.profile_edit_image',
      name='users_profile_edit_image'),
  url(r'^profile/edit/ajax_image/$', 'users.views.profile_edit_image_async',
      name='users_profile_edit_image_async'),
  url(r'^profile/edit/links/$', 'users.views.profile_edit_links',
      name='users_profile_edit_links'),
  url(r'^profile/edit/links/delete/(?P<link>[\d]+)/$',
      'users.views.profile_edit_links_delete',
      name='users_profile_edit_links_delete'),
  url(r'^profile/create/$', 'users.views.profile_create',
      name='users_profile_create'),
)

########NEW FILE########
__FILENAME__ = views
import logging

from django import http
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import views as auth_views
from django.contrib.auth import forms as auth_forms
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.views.decorators.http import require_http_methods
from django.forms import ValidationError

from django_openid_auth import views as openid_views
from commonware.decorators import xframe_sameorigin

from users import forms
from users.models import UserProfile
from users.fields import UsernameField
from users.decorators import anonymous_only, login_required
from links.models import Link
from links import forms as link_forms
from projects.models import Project
from drumbeat import messages
from activity.models import Activity

log = logging.getLogger(__name__)


def unconfirmed_account_notice(request, user):
    log.info(u'Attempt to log in with unconfirmed account (%s)' % user)
    msg1 = _(('A link to activate your user account was sent by email '
              'to your address {0}. You have to click it before you '
              'can log in.').format(user.email))
    url = request.build_absolute_uri(
        reverse('users_confirm_resend',
                kwargs=dict(username=user.username)))
    msg2 = _(('If you did not receive the confirmation email, make '
              'sure your email service did not mark it as "junk '
              'mail" or "spam". If you need to, you can have us '
              '<a href="%s">resend the confirmation message</a> '
              'to your email address mentioned above.') % url)
    messages.error(request, msg1)
    messages.info(request, msg2, safe=True)


def render_openid_failure(request, message, status, template_name):
    if request.method == 'POST':
        form = forms.OpenIDForm(request.POST)
    else:
        form = forms.OpenIDForm()
    response = render_to_string(template_name, {
        'message': message,
        'form': form,
    }, context_instance=RequestContext(request))
    return http.HttpResponse(response, status=status)


def render_openid_registration_failure(request, message, status=403):
    return render_openid_failure(
        request, message, status, 'users/register_openid.html')


def render_openid_login_failure(request, message, status=403):
    return render_openid_failure(
        request, message, status, 'users/login_openid.html')


def _clean_redirect_url(request):
    """Taken from zamboni. Prevent us from redirecting outside of drumbeat."""
    gets = request.GET.copy()
    url = gets[REDIRECT_FIELD_NAME]
    if url and '://' in url:
        url = None
    gets[REDIRECT_FIELD_NAME] = url
    request.GET = gets
    return request


def _get_redirect_url(request):
    url = request.session.get(REDIRECT_FIELD_NAME, None)
    if url:
        del request.session[REDIRECT_FIELD_NAME]
        if not url.startswith('/'):
            url = '/%s' % (url,)
        return url


@anonymous_only
def login(request):
    """Log the user in. Lifted most of this code from zamboni."""

    if REDIRECT_FIELD_NAME in request.GET:
        request = _clean_redirect_url(request)
        request.session[REDIRECT_FIELD_NAME] = request.GET[REDIRECT_FIELD_NAME]

    logout(request)

    r = auth_views.login(request, template_name='users/signin.html',
                         authentication_form=forms.AuthenticationForm)

    if isinstance(r, http.HttpResponseRedirect):
        # Succsesful log in according to django.  Now we do our checks.  I do
        # the checks here instead of the form's clean() because I want to use
        # the messages framework and it's not available in the request there
        user = request.user.get_profile()

        if user.confirmation_code:
            logout(request)
            unconfirmed_account_notice(request, user)
            return render_to_response('users/signin.html', {
                'form': auth_forms.AuthenticationForm(),
            }, context_instance=RequestContext(request))

        if request.POST.get('remember_me', None):
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            log.debug(u'User signed in with remember_me option')

        redirect_url = _get_redirect_url(request)
        if redirect_url:
            return http.HttpResponseRedirect(redirect_url)

    elif request.method == 'POST':
        messages.error(request, _('Incorrect email or password.'))
        # run through auth_views.login again to render template with messages.
        r = auth_views.login(request, template_name='users/signin.html',
                         authentication_form=forms.AuthenticationForm)

    return r


@anonymous_only
def login_openid(request):
    if request.method == 'POST':
        return openid_views.login_begin(
            request,
            template_name='users/login_openid.html',
            form_class=forms.OpenIDForm,
            login_complete_view='users_login_openid_complete')
    else:
        form = forms.OpenIDForm()
    return render_to_response('users/login_openid.html', {
        'form': form,
    }, context_instance=RequestContext(request))


@anonymous_only
def login_openid_complete(request):
    setattr(settings, 'OPENID_CREATE_USERS', False)
    r = openid_views.login_complete(
        request, render_failure=render_openid_login_failure)
    if isinstance(r, http.HttpResponseRedirect):
        try:
            user = request.user.get_profile()
        except UserProfile.DoesNotExist:
            user = request.user
            username = ''
            if user.username[:10] != 'openiduser':
                username = user.username
            form = forms.CreateProfileForm(initial={
                'display_name': ' '.join((user.first_name, user.last_name)),
                'email': user.email,
                'username': username,
            })
            return render_to_response('dashboard/setup_profile.html', {
                'form': form,
            }, context_instance=RequestContext(request))
        if user.confirmation_code:
            logout(request)
            unconfirmed_account_notice(request, user)
            return render_to_response('users/login_openid.html', {
                'form': forms.OpenIDForm(),
            }, context_instance=RequestContext(request))

        redirect_url = _get_redirect_url(request)
        if redirect_url:
            return http.HttpResponseRedirect(redirect_url)

    return r


@login_required(profile_required=False)
def logout(request):
    """Destroy user session."""
    auth.logout(request)
    return http.HttpResponseRedirect(reverse('dashboard_index'))


@anonymous_only
def register(request):
    """Present user registration form and handle registrations."""

    if REDIRECT_FIELD_NAME in request.GET:
        request = _clean_redirect_url(request)
        request.session[REDIRECT_FIELD_NAME] = request.GET[REDIRECT_FIELD_NAME]

    if request.method == 'POST':
        form = forms.RegisterForm(data=request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.generate_confirmation_code()
            user.save()
            user.create_django_user()

            log.info(u"Registered new account for user (%s)", user)

            messages.success(request, _('Congratulations! Your user account '
                                        'was successfully created.'))
            path = reverse('users_confirm_registration', kwargs={
                'username': user.username,
                'token': user.confirmation_code,
            })
            url = request.build_absolute_uri(path)
            user.email_confirmation_code(url)
            msg = _('Thanks! We have sent an email to {0} with '
                    'instructions for completing your '
                    'registration.').format(user.email)
            messages.info(request, msg)

            return http.HttpResponseRedirect(reverse('users_login'))
        else:
            messages.error(request, _('There are errors in this form. Please '
                                      'correct them and resubmit.'))
    else:
        form = forms.RegisterForm()
    return render_to_response('users/register.html', {
        'form': form,
    }, context_instance=RequestContext(request))


@anonymous_only
def register_openid(request):
    if request.method == 'POST':
        r = openid_views.login_begin(
            request,
            template_name='users/register_openid.html',
            form_class=forms.OpenIDForm,
            login_complete_view='users_register_openid_complete')
        return r
    else:
        form = forms.OpenIDForm()
    return render_to_response('users/register_openid.html', {
        'form': form,
    }, context_instance=RequestContext(request))


@anonymous_only
def register_openid_complete(request):
    setattr(settings, 'OPENID_CREATE_USERS', True)
    return openid_views.login_complete(
        request, render_failure=render_openid_registration_failure)


def user_list(request):
    """Display a list of users on the site. Featured, new and active."""
    featured = UserProfile.objects.filter(featured=True)
    new = UserProfile.objects.all().order_by('-created_on')[:4]
    popular = UserProfile.objects.get_popular(limit=8)
    return render_to_response('users/user_list.html', {
        'featured': featured,
        'new': new,
        'popular': popular,
    }, context_instance=RequestContext(request))


@anonymous_only
def confirm_registration(request, token, username):
    """Confirm a users registration."""
    profile = get_object_or_404(UserProfile, username=username)
    if profile.confirmation_code != token:
        messages.error(
            request,
           _('Hmm, that doesn\'t look like the correct confirmation code'))
        log.info('Account confirmation failed for %s' % (profile,))
        return http.HttpResponseRedirect(reverse('users_login'))
    profile.confirmation_code = ''
    profile.save()
    messages.success(request, 'Success! You have verified your account. '
                     'You may now sign in.')
    return http.HttpResponseRedirect(reverse('users_login'))


@anonymous_only
def confirm_resend(request, username):
    """Resend a confirmation code."""
    profile = get_object_or_404(UserProfile, username=username)
    if profile.confirmation_code:
        path = reverse('users_confirm_registration', kwargs={
            'username': profile.username,
            'token': profile.confirmation_code,
        })
        url = request.build_absolute_uri(path)
        profile.email_confirmation_code(url)
        msg = _('A confirmation code has been sent to the email address '
                'associated with your account.')
        messages.info(request, msg)
    return http.HttpResponseRedirect(reverse('users_login'))


def profile_view(request, username):
    profile = get_object_or_404(UserProfile, username=username)
    following = profile.following()
    projects = profile.following(model=Project)
    followers = profile.followers()
    links = Link.objects.select_related('subscription').filter(user=profile)
    activities = Activity.objects.for_user(profile)
    return render_to_response('users/profile.html', {
        'profile': profile,
        'following': following,
        'followers': followers,
        'projects': projects,
        'skills': profile.tags.filter(category='skill'),
        'interests': profile.tags.filter(category='interest'),
        'links': links,
        'activities': activities,
    }, context_instance=RequestContext(request))


@login_required(profile_required=False)
@require_http_methods(['POST'])
def profile_create(request):
    try:
        request.user.get_profile()
        return http.HttpResponseRedirect(reverse('dashboard_index'))
    except UserProfile.DoesNotExist:
        pass
    form = forms.CreateProfileForm(request.POST)
    if form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.user.email = profile.email
        profile.confirmation_code = profile.generate_confirmation_code()
        profile.save()
        profile.user.save()
        path = reverse('users_confirm_registration', kwargs={
            'username': profile.username,
            'token': profile.confirmation_code,
        })
        url = request.build_absolute_uri(path)
        profile.email_confirmation_code(url)
        auth.logout(request)
        msg = _('Thanks! We have sent an email to {0} with '
                'instructions for completing your '
                'registration.').format(profile.email)
        messages.info(request, msg)
        return http.HttpResponseRedirect(reverse('dashboard_index'))
    else:
        messages.error(request, _('There are errors in this form. Please '
                                      'correct them and resubmit.'))
    return render_to_response('dashboard/setup_profile.html', {
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
def profile_edit(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = forms.ProfileEditForm(request.POST, request.FILES,
                                     instance=profile)
        if form.is_valid():
            messages.success(request, _('Profile updated'))
            form.save()
            return http.HttpResponseRedirect(
                reverse('users_profile_edit'),
            )
        else:
            messages.error(request, _('There were problems updating your '
                                      'profile. Please correct the problems '
                                      'and submit again.'))
    else:
        form = forms.ProfileEditForm(instance=profile)

    return render_to_response('users/profile_edit_main.html', {
        'profile': profile,
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
@xframe_sameorigin
@require_http_methods(['POST'])
def profile_edit_image_async(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    form = forms.ProfileImageForm(request.POST, request.FILES,
                                  instance=profile)
    if form.is_valid():
        instance = form.save()
        return http.HttpResponse(simplejson.dumps({
            'filename': instance.image.name,
        }))
    return http.HttpResponse(simplejson.dumps({
        'error': 'There was an error uploading your image.',
    }))


@login_required
def profile_edit_image(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = forms.ProfileImageForm(request.POST, request.FILES,
                                      instance=profile)
        if form.is_valid():
            messages.success(request, _('Profile image updated'))
            form.save()
            return http.HttpResponseRedirect(
                reverse('users_profile_edit_image'))
        else:
            messages.error(request, _('There was an error uploading '
                                      'your image.'))
    else:
        form = forms.ProfileImageForm(instance=profile)

    return render_to_response('users/profile_edit_image.html', {
        'profile': profile,
        'form': form,
    }, context_instance=RequestContext(request))


@login_required
def profile_edit_links(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = link_forms.LinksForm(request.POST)
        if form.is_valid():
            messages.success(request, _('Profile link added.'))
            link = form.save(commit=False)
            log.debug("User instance: %s" % (profile.user,))
            link.user = profile
            link.save()
            return http.HttpResponseRedirect(
                reverse('users_profile_edit_links'),
            )
        else:
            messages.error(request, _('There was an error saving '
                                      'your link.'))
    else:
        form = link_forms.LinksForm()
    links = Link.objects.select_related('subscription').filter(user=profile)

    return render_to_response('users/profile_edit_links.html', {
        'profile': profile,
        'form': form,
        'links': links,
    }, context_instance=RequestContext(request))


@login_required
def profile_edit_links_delete(request, link):
    if request.method == 'POST':
        profile = get_object_or_404(UserProfile, user=request.user)
        link = get_object_or_404(Link, pk=link)
        if link.user != profile:
            return http.HttpResponseForbidden()
        link.delete()
        messages.success(request, _('The link was deleted.'))
    return http.HttpResponseRedirect(reverse('users_profile_edit_links'))


def check_username(request):
    """Validate a username and check for uniqueness."""
    username = request.GET.get('username', None)
    f = UsernameField()
    try:
        f.clean(username)
    except ValidationError:
        return http.HttpResponse()
    try:
        UserProfile.objects.get(username=username)
        return http.HttpResponse()
    except UserProfile.DoesNotExist:
        pass
    return http.HttpResponse(status=404)


@login_required
def following(request):
    user = request.user.get_profile()
    term = request.GET.get('term', '').lower()
    usernames = [u.username for u in user.following()
                 if term in u.username.lower() or
                 term in u.display_name.lower()]
    return http.HttpResponse(simplejson.dumps(usernames),
                             mimetype='application/json')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import site

from django.core.management import execute_manager

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

site.addsitedir(path('apps'))

try:
    import settings_local as settings
except ImportError:
    try:
        import settings 
    except ImportError:
        import sys
        sys.stderr.write(
            "Error: Tried importing 'settings_local.py' and 'settings.py' "
            "but neither could be found (or they're throwin an ImportError)."
            " Please come back and try later.")
        raise

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for batucada project.

import os
import logging
import djcelery

djcelery.setup_loader()

# Make filepaths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT, *a)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'batucada.db',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Toronto'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

SUPPORTED_NONLOCALES = ('media', '.well-known', 'pubsub', 'broadcasts', 'ajax')

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin-media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'std3j$ropgs216z1aa#8+p3a2w2q06mns_%2vfx_#$$i!+6o+x'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# Set HttpOnly flag on session cookies
SESSION_COOKIE_HTTPONLY = True

# Hack to get HttpOnly flag set on session cookies. This can be removed when
# http://code.djangoproject.com/changeset/14707 makes it into a release.
SESSION_COOKIE_PATH = '/; HttpOnly'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'l10n.middleware.LocaleURLRewriter',
    'django.middleware.common.CommonMiddleware',
    'commonware.middleware.HidePasswordOnException',
    'commonware.middleware.FrameOptionsHeader',
    'jogging.middleware.LoggingMiddleware',
)

ROOT_URLCONF = 'batucada.urls'

TEMPLATE_DIRS = (
    path('templates'),
)

INSTALLED_APPS = (
    'django.contrib.sites',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.comments',
    'south',
    'jogging',
    'wellknown',
    'users',
    'l10n',
    'dashboard',
    'relationships',
    'activity',
    'projects',
    'statuses',
    'messages',
    'drumbeat',
    'taggit',
    'preferences',
    'drumbeatmail',
    'links',
    'challenges',
    'django_push.subscriber',
    'djcelery',
    'events',
    'django_openid_auth',
    'voting', 
    'feeds',
    'assetmanager',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'drumbeat.context_processors.django_conf',
    'messages.context_processors.inbox',
    'users.context_processors.messages',
    'users.context_processors.redirect_urls',
    'feeds.context_processors.feed_entries',
)

TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner'

WELLKNOWN_HOSTMETA_HOSTS = ('localhost:8000',)

# Auth settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

ACCOUNT_ACTIVATION_DAYS = 7

AUTHENTICATION_BACKENDS = (
    'users.backends.CustomUserBackend',
    'django_openid_auth.auth.OpenIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

AUTH_PROFILE_MODULE = 'users.UserProfile'

MAX_IMAGE_SIZE = 1024 * 700
MAX_UPLOAD_SIZE = 1024 * 1024 * 50
MAX_PROJECT_FILES = 6

GLOBAL_LOG_LEVEL = logging.DEBUG
GLOBAL_LOG_HANDLERS = [logging.StreamHandler()]

CACHE_BACKEND = 'caching.backends.memcached://localhost:11211'
CACHE_PREFIX = 'batucada'
CACHE_COUNT_TIMEOUT = 60

# Email goes to the console by default.  s/console/smtp/ for regular delivery
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Mozilla Drumbeat <drumbeat@mozilla.org>'

# Copy these to your settings_local.py
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_URL = ('https://api-secure.recaptcha.net/challenge?k=%s' %
                 RECAPTCHA_PUBLIC_KEY)

# RabbitMQ Config
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = ""
BROKER_PASSWORD = ""
BROKER_VHOST = ""

CELERY_RESULT_BACKEND = "amqp"

# SuperFeedr settings
SUPERFEEDR_URL = 'http://superfeedr.com/hubbub'
SUPERFEEDR_USERNAME = ''
SUPERFEEDR_PASSWORD = ''

# django-push settings
PUSH_CREDENTIALS = 'links.utils.hub_credentials'
PUSH_HUB = 'http://pubsubhubbub.appspot.com/'
SOUTH_TESTS_MIGRATE = False

# Feed to show contents of on the splash page
FEED_URLS = {
    'splash': 'http://planet.drumbeat.org/atom.xml',
    'mojo': 'http://planet.drumbeat.org/mojo/atom.xml',
}

SPLASH_PAGE_FEED = 'http://planet.drumbeat.org/atom.xml'

# Would be awesome if this could somehow be dynamic - no idea how though...
ASSETS = {
    'css':{
        'site' : {
            'dev':(
                'css/style.css',
                'css/batucada.css',
                'css/template.css'
            ),
            'live':('css/packs/site.css',)
        },
        'mojo':{
            'dev':(
                'css/style.css',
                'css/mojo.css',
            ),
            'live':('css/packs/mojo.css',)
        }
    },
    'js':{
        'styling' : {
            'dev':(
                'fonts/MuseoSans500/MuseoSans500.js',
                'js/common/ext/modernizr-1.6.min.js'
            ),
            'live':('js/packs/styling.js',)
        },
        'libraries' : {
            'dev':(
                'js/common/ext/LAB.min.js',
                'js/common/ext/jquery-1.4.2.min.js',
                'js/common/ext/jquery.easing.1.3.js',
                'js/common/plugins.js',
                'js/common/script.js'
            ),
            'live':('js/packs/libs.js',)
        }
    }
}

########NEW FILE########
__FILENAME__ = settings_local.dist
from settings import *

# Useful settings for running a local instance of batucada.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'NAME': 'batucada',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '',
        'PORT': '',
        'USER': 'root',
        'PASSWORD': '',
        'OPTIONS': {'init_command': 'SET storage_engine=InnoDB'},
    }
}

TIME_ZONE = 'America/Toronto'

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
)

MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)
INTERNAL_IPS = ('127.0.0.1',)

# Use dummy caching for development.
CACHE_BACKEND = 'dummy://'
CACHE_PREFIX = 'batucada'
CACHE_COUNT_TIMEOUT = 60

# Execute celery tasks locally, so you don't have to be running an MQ
CELERY_ALWAYS_EAGER = True

# Path to ffmpeg. This will have to be installed to create video thumbnails
FFMPEG_PATH = '/usr/bin/ffmpeg'

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import *
from django.http import HttpResponsePermanentRedirect

from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/',         include(admin.site.urls)),
    (r'',                include('drumbeat.urls')),
    (r'',                include('dashboard.urls')),
    (r'^challenges/',    include('challenges.urls')),
    (url(r'^P2PU/', lambda x: HttpResponsePermanentRedirect('http://www.p2pu.org'))),
    (url(r'^webmademovies', lambda x: HttpResponsePermanentRedirect('http://mozillapopcorn.org/'))),
    (url(r'^events/', lambda x: HttpResponsePermanentRedirect('https://www.mozillafestival.org/'))),
    (url(r'^projects/(?P<slug>[\w-]+)/$', 'projects.views.move_on')),
)

media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
urlpatterns += patterns('',
    (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
     {
         'document_root': settings.MEDIA_ROOT,
     }),
)

urlpatterns += patterns('',
    (r'',                'drumbeat.views.drumbeat_retired'), 
    (r'',                include('wellknown.urls')),
    (r'',                include('activity.urls')),
    (r'^statuses/',      include('statuses.urls')),
    (r'^projects/',      include('projects.urls')),
    (r'^events/',        include('events.urls')),
    (r'^relationships/', include('relationships.urls')),
    (r'^messages/',      include('drumbeatmail.urls')),
    (r'^account/',       include('preferences.urls')),
    (r'^pubsub/',        include('django_push.subscriber.urls')),
    (r'',                include('users.urls')),    
)

handler500 = 'drumbeat.views.server_error'

########NEW FILE########
